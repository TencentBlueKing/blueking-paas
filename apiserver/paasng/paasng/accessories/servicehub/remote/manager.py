# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""The universal services module, handles both services from database and remote REST API"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterable, Iterator, List, Optional, cast

import arrow
import cattrs
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.networking.egress.shim import get_cluster_egress_info
from paasng.accessories.servicehub import constants, exceptions
from paasng.accessories.servicehub.binding_policy.selector import PlanSelector, get_plan_by_env
from paasng.accessories.servicehub.exceptions import (
    BindServicePlanError,
    UnboundSvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.models import (
    RemoteServiceEngineAppAttachment,
    RemoteServiceModuleAttachment,
    UnboundRemoteServiceEngineAppAttachment,
)
from paasng.accessories.servicehub.remote.client import RemoteServiceClient
from paasng.accessories.servicehub.remote.collector import refresh_remote_service
from paasng.accessories.servicehub.remote.exceptions import (
    GetClusterEgressInfoError,
    RClientResponseError,
    ServiceNotFound,
    UnsupportedOperationError,
)
from paasng.accessories.servicehub.remote.store import RemoteServiceStore
from paasng.accessories.servicehub.services import (
    NOTSET,
    BasePlanMgr,
    BaseServiceMgr,
    EngineAppInstanceRel,
    PlainInstanceMgr,
    PlanObj,
    ServiceInstanceObj,
    ServiceObj,
    UnboundEngineAppInstanceRel,
)
from paasng.accessories.services.models import ServiceCategory
from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.misc.metrics import SERVICE_PROVISION_COUNTER
from paasng.platform.applications.models import Application, ApplicationEnvironment, ModuleEnvironment
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    import datetime

    from paasng.platform.engine.constants import AppEnvName

logger = logging.getLogger(__name__)


@dataclass
class MetaInfo:
    """Remote service's meta info, including `version` and other information.

    We could use it to archive a lot of things. such as checking if a feature was available in current service.
    """

    version: Optional[str]

    def semantic_version_gte(self, version: str) -> bool:
        """Check if version is greater than or equal with given version

        - '0.12.3' >= '0.3.4'
        """
        if not self.version:
            return False

        parts = self.version.split(".")
        given_parts = version.split(".")
        for i, j in zip(parts, given_parts):
            if int(i) > int(j):
                return True
            if int(i) < int(j):
                return False
        return parts == given_parts


DEFAULT_META_INFO = MetaInfo(version=None)
VERSION_WITH_INST_CONFIG = "0.1.0"
VERSION_WITH_REST_UPSERT = "0.2.0"


@dataclass
class RemotePlanObj(PlanObj):
    @classmethod
    def from_data(cls, data: Dict):
        data.setdefault("is_active", True)
        properties = data.get("properties") or {}
        is_eager = data.pop("is_eager", False)
        config = data.pop("config", {})
        # Handle malformed config data used by some legacy services
        if config == "不支持":
            config = {}
        # Configure a default tenant_id for the planObj when the remote service is not upgraded.
        # NOTE: If the remote service is not upgraded to support multi-tenancy, the planObj must be under the default tenant.
        default_tenant_id = get_init_tenant_id()
        tenant_id = data.pop("tenant_id", default_tenant_id)
        return cattrs.structure(
            {"is_eager": properties.get("is_eager", is_eager), "config": config, "tenant_id": tenant_id} | data, cls
        )


@dataclass
class RemoteServiceObj(ServiceObj):
    plans: List[RemotePlanObj] = field(default_factory=list)
    meta_info: MetaInfo = field(default_factory=lambda: MetaInfo(version=None))

    _data = None
    category_id = None

    @classmethod
    def from_data(cls, service: Dict) -> "RemoteServiceObj":
        field_names = list(cls.__dataclass_fields__.keys())  # type: ignore
        fields: Dict[str, Any] = {k: service.get(k) for k in field_names if k in service}
        fields["plans"] = [asdict(RemotePlanObj.from_data(i)) for i in fields.get("plans") or ()]

        # Set up meta info
        meta_info_data = service.get("_meta_info")
        if not meta_info_data:
            fields["meta_info"] = {"version": None}
        else:
            fields["meta_info"] = {"version": meta_info_data["version"]}

        result = cattrs.structure(fields, cls)
        result._data = service
        result.category_id = service["category"]
        return result

    @property
    def category(self):
        if not self._data:
            raise RuntimeError('RemoteServiceObj requires "_data" attribute')
        return ServiceCategory.objects.get(pk=self._data["category"])

    def get_plans(self, is_active=True) -> List["PlanObj"]:
        return [plan.with_service(self) for plan in self.plans if (plan.is_active == is_active or is_active is NOTSET)]

    def get_plans_by_tenant_id(self, tenant_id: str, is_active=True) -> List["PlanObj"]:
        all_plans = self.get_plans(is_active=is_active)
        return [plan for plan in all_plans if (plan.tenant_id == tenant_id)]

    def supports_inst_config(self) -> bool:
        """Check if current service supports Feature: InstanceConfig"""
        return self.meta_info.semantic_version_gte(VERSION_WITH_INST_CONFIG)

    def supports_rest_upsert(self) -> bool:
        """Check if current service supports Feature: RestFul upsert Service/Plan"""
        return self.meta_info.semantic_version_gte(VERSION_WITH_REST_UPSERT)


@dataclass
class EnvClusterInfo:
    env: "ModuleEnvironment"

    def get_egress_info(self):
        """Get current app cluster egress info
        {"egress_ips": [<IP>, ], "digest_version": <DIGEST_VERSION>}
        """
        try:
            return get_cluster_egress_info(EnvClusterService(self.env).get_cluster_name())
        except Exception as e:
            logger.exception("Can not get app cluster egress info")
            raise GetClusterEgressInfoError(str(e))

    @cached_property
    def egress_info_json(self):
        egress_info = self.get_egress_info()
        return json.dumps(egress_info)


class RemoteEngineAppInstanceRel(EngineAppInstanceRel):
    """A relationship between EngineApp and Provisioned instance"""

    def __init__(self, db_obj: RemoteServiceEngineAppAttachment, mgr: "RemoteServiceMgr", store: RemoteServiceStore):
        self.store = store
        self.mgr = mgr

        # Database objects
        self.db_obj = db_obj
        self.db_env = ModuleEnvironment.objects.get(engine_app=self.db_obj.engine_app)
        self.db_engine_app = self.db_obj.engine_app
        self.db_application = self.db_env.application
        self.db_module = self.db_env.module

        # Client components
        self.remote_config = self.store.get_source_config(str(self.db_obj.service_id))
        self.remote_client = RemoteServiceClient(self.remote_config)

    def get_service(self) -> RemoteServiceObj:
        return self.mgr.get(str(self.db_obj.service_id))

    def is_provisioned(self) -> bool:
        return self.db_obj.service_instance_id is not None

    def provision(self):
        """Provision a real service instance

        :raises: ProvisionInstanceError
        """
        if self.is_provisioned():
            logger.warning(f"remote instance {self.db_obj.pk} already provisioned, skip")
            return

        if not self.remote_config.is_ready:
            logger.warning(f"remote service {self.get_service().name} is not ready, skip")
            return

        instance_id = str(uuid.uuid4())
        try:
            params = self.render_params(self.remote_config.provision_params_tmpl)
            self.remote_client.provision_instance(
                str(self.db_obj.service_id), str(self.db_obj.plan_id), instance_id, params=params
            )
        except Exception as e:
            logger.exception(f"Error provisioning new instance for {self.db_application.name}")
            raise exceptions.ProvisionInstanceError(
                _("配置资源实例异常: unable to provision instance for services<{service_name}>").format(
                    service_name=self.get_service().name
                )
            ) from e

        service_obj = self.get_service()

        # Write back to database
        self.db_obj.service_instance_id = instance_id
        self.db_obj.save(update_fields=["service_instance_id"])

        # Update instance config
        if service_obj.supports_inst_config():
            self.sync_instance_config()

        SERVICE_PROVISION_COUNTER.labels(
            environment=self.db_env.environment,
            service=service_obj.name,
            # TODO: get plan from remote service
            plan="",
        ).inc()

    def sync_instance_config(self):
        """Sync instance config with remote service"""
        paas_app_info: Dict[str, str] = {
            "app_id": str(self.db_application.id),
            "app_code": str(self.db_application.code),
            "app_name": str(self.db_application.name),
            "module": self.db_module.name,
            "environment": self.db_env.environment,
        }
        instance_id = self.db_obj.service_instance_id
        if not instance_id:
            raise ValueError("Relationship not provisioned, no instance_id can be found")

        try:
            self.remote_client.update_instance_config(instance_id, config={"paas_app_info": paas_app_info})
        except Exception:
            logger.exception(f"Error when updating instance config for {instance_id}")

    def recycle_resource(self):
        """对于 remote service 我们默认其已经具备了回收的能力"""
        if self.is_provisioned():
            try:
                self.remote_client.delete_instance(instance_id=str(self.db_obj.service_instance_id))
            except Exception as e:
                logger.exception("Error occurs during recycling")
                raise exceptions.SvcInstanceDeleteError("unable to delete instance") from e

            if self.remote_client.config.prefer_async_delete:
                UnboundRemoteServiceEngineAppAttachment.objects.create(
                    owner=self.db_obj.owner,
                    engine_app=self.db_engine_app,
                    service_id=self.db_obj.service_id,
                    service_instance_id=self.db_obj.service_instance_id,
                    tenant_id=self.db_obj.tenant_id,
                )

        self.db_obj.service_instance_id = None
        self.db_obj.save()

    def get_instance(self) -> ServiceInstanceObj:
        """Get service instance object"""
        if not self.is_provisioned():
            raise ValueError("relationship is not provisioned yet")

        # TODO: failure tolerance
        instance_data = self.remote_client.retrieve_instance(str(self.db_obj.service_instance_id))
        # TODO: More data validations
        if not instance_data.get("uuid") == str(self.db_obj.service_instance_id):
            raise exceptions.SvcInstanceNotAvailableError("uuid in data does not match")

        svc_obj = self.get_service()
        create_time = arrow.get(instance_data.get("created"))  # type: ignore
        default_tenant_id = get_init_tenant_id()
        return create_svc_instance_obj_from_remote(
            uuid=str(self.db_obj.service_instance_id),
            credentials=instance_data["credentials"],
            config=instance_data["config"],
            tenant_id=instance_data.get("tenant_id", default_tenant_id),
            field_prefix=svc_obj.name,
            create_time=create_time.datetime,
        )

    def render_params(self, params_tmpl: Dict) -> Dict:
        """ "Render params dict by current rel's context, Available keys:

        Database objects:

        - `engine_app`: current EngineApp object
        - `application`: current Application object
        - `module`: current Module object
        - `env`: current ModuleEnvironment object
        """
        result = {}
        cluster_info = EnvClusterInfo(self.db_env)

        bk_monitor_space_id = ""
        # 增强服务参数中声明了需要蓝鲸监控命名空间，则需要创建应用对应的蓝鲸监控命名空间
        if "bk_monitor_space_id" in params_tmpl:
            # 蓝鲸监控命名空间的成员只能初始化一个成员，默认初始化应用的创建者
            # 已测试用离职用户也能创建成功
            space, _ = get_or_create_bk_monitor_space(self.db_application)
            # TODO: 统一术语
            bk_monitor_space_id = space.space_uid

        for key, tmpl_str in params_tmpl.items():
            result[key] = tmpl_str.format(
                engine_app=self.db_engine_app,
                application=self.db_application,
                module=self.db_module,
                env=self.db_env,
                cluster_info=cluster_info,
                app_developers=json.dumps(self.db_application.get_developers()),
                bk_monitor_space_id=bk_monitor_space_id,
            )
        return result

    def get_plan(self) -> RemotePlanObj:
        plan_id = str(self.db_obj.plan_id)
        # 兼容从v2迁移至v3的增强服务, 避免前端因此出现异常
        if plan_id == str(constants.LEGACY_PLAN_ID):
            return RemotePlanObj.from_data(constants.LEGACY_PLAN_INSTANCE)

        svc_data = self.store.get(str(self.db_obj.service_id))
        for d in svc_data["plans"]:
            if d["uuid"] == plan_id:
                return RemotePlanObj.from_data(d)

        raise RuntimeError("Plan not found")


class UnboundRemoteEngineAppInstanceRel(UnboundEngineAppInstanceRel):
    """Unbound relationship between EngineApp and remote provisioned instance"""

    def __init__(
        self, db_obj: UnboundRemoteServiceEngineAppAttachment, mgr: "RemoteServiceMgr", store: RemoteServiceStore
    ):
        self.store = store
        self.mgr = mgr

        # Database objects
        self.db_obj = db_obj
        self.db_env = ModuleEnvironment.objects.get(engine_app=self.db_obj.engine_app)
        self.db_application = self.db_env.application

        # Client components
        self.remote_config = self.store.get_source_config(str(self.db_obj.service_id))
        self.remote_client = RemoteServiceClient(self.remote_config)

    def _retrieve_instance_to_be_deleted(self) -> dict:
        try:
            instance_data = self.remote_client.retrieve_instance_to_be_deleted(str(self.db_obj.service_instance_id))
        except RClientResponseError as e:
            # If not found service instance by instance id, which means it has been recycled, remote will return 404.
            if e.status_code == 404:
                self.db_obj.delete()
                return {}
            raise
        return instance_data

    def get_instance(self) -> Optional[ServiceInstanceObj]:
        """Get service instance object"""
        instance_data = self._retrieve_instance_to_be_deleted()
        if not instance_data:
            return None
        svc_obj = self.mgr.get(str(self.db_obj.service_id))
        create_time = arrow.get(instance_data.get("created"))  # type: ignore
        default_tenant_id = get_init_tenant_id()
        return create_svc_instance_obj_from_remote(
            uuid=str(self.db_obj.service_instance_id),
            credentials=instance_data["credentials"],
            config=instance_data["config"],
            tenant_id=instance_data.get("tenant_id", default_tenant_id),
            field_prefix=svc_obj.name,
            create_time=create_time.datetime,
        )

    def recycle_resource(self) -> None:
        """Recycle unbound service instance resource synchronously"""
        try:
            self.remote_client.delete_instance_synchronously(instance_id=str(self.db_obj.service_instance_id))
        except RClientResponseError as e:
            # If not found service instance by instance id, which means it has been recycled, remote will return 404.
            if e.status_code == 404:
                pass
            else:
                logger.exception("Error occurs during recycling")
                raise exceptions.SvcInstanceDeleteError("unable to delete instance") from e

        self.db_obj.delete()
        logger.info(
            f"Manually recycled unbound remote service instance, service_id: {self.db_obj.service_id}, service_instance_id: {self.db_obj.service_instance_id}"
        )


class RemotePlainInstanceMgr(PlainInstanceMgr):
    """纯粹的远程增强服务实例的管理器, 仅调用远程接口创建增强服务实例, 不涉及增强服务资源申请的流程"""

    def __init__(self, db_obj: RemoteServiceEngineAppAttachment, mgr: "RemoteServiceMgr"):
        self.mgr = mgr
        # Database objects
        self.db_obj = db_obj
        self.db_env = ModuleEnvironment.objects.get(engine_app=self.db_obj.engine_app)
        self.db_engine_app = self.db_obj.engine_app
        self.db_application = self.db_env.application
        self.db_module = self.db_env.module

        self.remote_client = self.get_remote_client()

    def get_service(self) -> RemoteServiceObj:
        return self.mgr.get(str(self.db_obj.service_id))

    def get_remote_client(self):
        remote_config = self.mgr.store.get_source_config(str(self.db_obj.service_id))
        remote_client = RemoteServiceClient(remote_config)
        return remote_client

    def sync_instance_config(self):
        """Sync instance config with remote service"""
        paas_app_info: Dict[str, str] = {
            "app_id": str(self.db_application.id),
            "app_code": str(self.db_application.code),
            "app_name": str(self.db_application.name),
            "module": self.db_module.name,
            "environment": self.db_env.environment,
        }
        instance_id = self.db_obj.service_instance_id
        if not instance_id:
            raise ValueError("Relationship not provisioned, no instance_id can be found")

        try:
            self.remote_client.update_instance_config(str(instance_id), config={"paas_app_info": paas_app_info})
        except Exception:
            logger.exception(f"Error when updating instance config for {instance_id}")

    def is_provisioned(self):
        return self.db_obj.service_instance_id is not None

    def create(self, credentials: Dict, config: Dict):
        """根据提供的 config, credentials 创建增强服务实例"""
        if self.is_provisioned():
            return

        service_obj = self.get_service()
        instance_id = str(uuid.uuid4())

        try:
            self.remote_client.create_client_side_instance(
                service_id=self.db_obj.service_id,
                instance_id=instance_id,
                params={"credentials": credentials, "config": config},
            )
        except Exception as e:
            logger.exception(f"Error bind instance for {self.db_application.name}")
            raise exceptions.BaseServicesException(
                _("绑定实例异常: unable to provision instance for services<{service_obj_name}>").format(
                    service_obj_name=service_obj.name
                )
            ) from e

        # Write back to database
        self.db_obj.service_instance_id = instance_id
        self.db_obj.save(update_fields=["service_instance_id", "updated"])

        # Update instance config
        if service_obj.supports_inst_config():
            self.sync_instance_config()

    def destroy(self):
        """删除增强服务实例记录, 但不回收资源"""
        if not self.is_provisioned():
            return

        self.remote_client.destroy_client_side_instance(instance_id=str(self.db_obj.service_instance_id))
        logger.info("going to delete remote service attachment from db")
        # delete rel itself from real db
        self.db_obj.delete()


def create_svc_instance_obj_from_remote(
    uuid: str, credentials: Dict, config: Dict, field_prefix: str, create_time: "datetime.datetime", tenant_id: str
) -> ServiceInstanceObj:
    """Create a Service Instance object for remote service

    special fields:

    - `config.__meta__`: if "should_hidden_fields" or "should_remove_fields" was included in this
        field, the value will be popped for instance initializing.
    """

    def _format_key(val):
        """
        Turn credential keys in to upper case and add prefix (svc name),
        also replace '-' with '_' to match the unix environment variable name format
        """
        key = f"{field_prefix}_{val}".upper()
        return key.replace("-", "_")

    _credentials = {_format_key(key): value for key, value in credentials.items()}

    # Parse and process meta configs
    meta_config = config.pop("__meta__", {})
    should_hidden_fields = list(map(_format_key, meta_config.get("should_hidden_fields", [])))
    should_remove_fields = list(map(_format_key, meta_config.get("should_remove_fields", [])))
    return ServiceInstanceObj(
        uuid, _credentials, config, tenant_id, should_hidden_fields, should_remove_fields, create_time
    )


class RemoteServiceMgr(BaseServiceMgr):
    """Remote REST services manager"""

    service_obj_cls = RemoteServiceObj

    def __init__(self, store: RemoteServiceStore):
        self.store = store

    def get(self, uuid: str) -> RemoteServiceObj:
        """Get a single service by given uuid

        :raises: ServiceObjNotFound
        """
        try:
            obj = self.store.get(uuid)
        except (ServiceNotFound, RuntimeError) as e:
            raise exceptions.ServiceObjNotFound(f"Service with id={uuid} not found in remote") from e
        return RemoteServiceObj.from_data(obj)

    def find_by_name(self, name: str) -> RemoteServiceObj:
        """Find a single service by service name

        :raises: ServiceObjNotFound
        """
        objs = self.store.filter(conditions={"name": name})
        if not objs:
            raise exceptions.ServiceObjNotFound(f"Service with name={name} not found in remote")
        # Use the first matched services objects
        return RemoteServiceObj.from_data(objs[0])

    def list_by_category(self, category_id: int, include_hidden=False) -> Generator[ServiceObj, None, None]:
        """query a list of services by category"""
        items = self.store.filter(conditions={"category": category_id})
        for svc in items:
            obj = RemoteServiceObj.from_data(svc)
            # Ignore services which is_visible field is False
            if not include_hidden and not svc["is_visible"]:
                continue
            yield obj

    def list_visible(self) -> Iterable[ServiceObj]:
        """list visible services."""
        items = self.store.all()
        for svc in items:
            if not svc["is_visible"]:
                continue
            yield RemoteServiceObj.from_data(svc)

    def list(self) -> Iterable[ServiceObj]:
        """List all services"""
        items = self.store.all()
        for svc in items:
            yield RemoteServiceObj.from_data(svc)

    def _handle_service_data(self, data: Dict) -> Dict:
        # 由于远程增强服务在存储 category_id 的字段命名为 category, 因此这里需要做个重命名
        data["category"] = data.pop("category_id")
        return data

    def update(self, service: ServiceObj, data: Dict):
        """update the service"""
        if not isinstance(service, RemoteServiceObj) or not service.supports_rest_upsert():
            raise UnsupportedOperationError("This service does not support update.")

        service_id = str(service.uuid)
        remote_config = self.store.get_source_config(service_id)
        remote_client = RemoteServiceClient(remote_config)

        data = self._handle_service_data(data)
        remote_client.update_service(service_id=service_id, data=data)
        # 更新 store 中的信息
        refresh_remote_service(self.store, service_id)

    def destroy(self, service: ServiceObj):
        raise UnsupportedOperationError("Remote Service does not support delete.")

    def list_binded(self, module: Module, category_id: Optional[int] = None) -> Iterator[ServiceObj]:
        """List application's bound services"""
        attachments = RemoteServiceModuleAttachment.objects.filter(module=module).values("service_id")
        service_ids = [str(obj["service_id"]) for obj in attachments]
        for svc in self.store.bulk_get(service_ids):
            if svc:
                obj = RemoteServiceObj.from_data(svc)
                if category_id and category_id != obj.category_id:
                    continue
                yield obj

    def bind_service(
        self,
        service: ServiceObj,
        module: Module,
        plan_id: str | None = None,
        env_plan_id_map: Dict[str, str] | None = None,
    ) -> str:
        """Bind a service to module"""
        binder = RemoteServiceBinder(service)
        return binder.bind(module, plan_id, env_plan_id_map).pk

    def bind_service_use_first_plan(self, service: ServiceObj, module: Module) -> str:
        """Bind a service to module, use the first plan when multiple plans are available"""
        binder = RemoteServiceBinder(service)
        return binder.bind_use_first_plan(module).pk

    def bind_service_partial(self, service: ServiceObj, module: Module) -> str:
        """Bind a service to module, without binding to engine app"""
        binder = RemoteServiceBinder(service)
        return binder.bind_without_plan(module).pk

    def list_all_rels(
        self, engine_app: EngineApp, service_id: Optional[str] = None
    ) -> Generator[RemoteEngineAppInstanceRel, None, None]:
        """Return all attachments with engine_app"""
        qs = engine_app.remote_service_attachment.all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        for attachment in qs:
            yield RemoteEngineAppInstanceRel(attachment, self, self.store)

    def get_module_rel(self, service_id: str, module_id: str) -> Any:
        try:
            attachment = RemoteServiceModuleAttachment.objects.get(module_id=module_id, service_id=service_id)
        except RemoteServiceModuleAttachment.DoesNotExist:
            raise exceptions.SvcAttachmentDoesNotExist("service attachment does not exist.")
        return attachment

    def list_unprovisioned_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[RemoteEngineAppInstanceRel, None, None]:
        """Return all unprovisioned engine_app <-> remote service instances"""
        qs = engine_app.remote_service_attachment.filter(service_instance_id__isnull=True)
        if service:
            qs = qs.filter(service_id=service.uuid)
        for attachment in qs:
            yield self.transform_rel_db_obj(attachment)

    def list_provisioned_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[RemoteEngineAppInstanceRel, None, None]:
        """Return all provisioned engine_app <-> remote service instances"""
        qs = engine_app.remote_service_attachment.exclude(service_instance_id__isnull=True)
        if service:
            qs = qs.filter(service_id=service.uuid)
        for attachment in qs:
            yield self.transform_rel_db_obj(attachment)

    def list_unbound_instance_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[UnboundRemoteEngineAppInstanceRel, None, None]:
        """Return all unbound remote service instances, filter by specific service (None for all)"""
        qs = engine_app.unbound_remote_service_attachment.all()
        if service:
            qs = qs.filter(service_id=service.uuid)
        for attachment in qs:
            yield UnboundRemoteEngineAppInstanceRel(attachment, self, self.store)

    def get_attachment_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        try:
            return RemoteServiceEngineAppAttachment.objects.get(
                service_id=service.uuid, service_instance_id=service_instance_id
            )
        except RemoteServiceEngineAppAttachment.DoesNotExist as e:
            raise exceptions.SvcAttachmentDoesNotExist from e

    def get_instance_rel_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        return self.transform_rel_db_obj(self.get_attachment_by_instance_id(service, service_instance_id))

    def get_provisioned_queryset(self, service: ServiceObj, application_ids: List[str]) -> QuerySet:
        """Return the queryset of provisioned db queryset by query condition"""
        modules = Module.objects.filter(application_id__in=application_ids)
        return RemoteServiceModuleAttachment.objects.filter(
            service_id=service.uuid,
            module__in=modules,
        )

    def transform_rel_db_obj(self, obj: RemoteServiceEngineAppAttachment) -> RemoteEngineAppInstanceRel:
        """Transform a db attachment to rel instance"""
        return RemoteEngineAppInstanceRel(obj, self, self.store)

    def module_is_bound_with(self, service: ServiceObj, module: Module) -> bool:
        """Check if a module is bound with a service"""
        return RemoteServiceModuleAttachment.objects.filter(module=module, service_id=service.uuid).exists()

    def get_provisioned_envs(self, service: ServiceObj, module: Module) -> List["AppEnvName"]:
        """Get a list of bound envs"""
        env_list = []
        for env in module.get_envs():
            if RemoteServiceEngineAppAttachment.objects.filter(
                engine_app=env.get_engine_app(), service_id=service.uuid, service_instance_id__isnull=False
            ).exists():
                env_list.append(env.environment)
        return env_list

    def get_mysql_services(self) -> List[RemoteServiceObj]:
        """Get all remote mysql services"""
        service_objects = []
        seen_uuids = set()
        for service_name in ["gcs_mysql", "mysql"]:
            try:
                svc = self.find_by_name(name=service_name)
            except exceptions.ServiceObjNotFound:
                continue
            if svc.uuid in seen_uuids:
                continue
            seen_uuids.add(svc.uuid)
            service_objects.append(svc)
        return service_objects

    def get_attachment_by_engine_app(self, service: ServiceObj, engine_app: EngineApp):
        """Get RemoteServiceEngineAppAttachment"""
        try:
            return RemoteServiceEngineAppAttachment.objects.get(service_id=service.uuid, engine_app=engine_app)
        except RemoteServiceEngineAppAttachment.DoesNotExist as e:
            raise exceptions.SvcAttachmentDoesNotExist from e

    def get_unbound_instance_rel_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        """Return a unbound remote service instances, filter by specific service and service instance id"""
        try:
            instance = UnboundRemoteServiceEngineAppAttachment.objects.get(
                service_id=service.uuid,
                service_instance_id=service_instance_id,
            )
        except UnboundRemoteServiceEngineAppAttachment.DoesNotExist as e:
            raise UnboundSvcAttachmentDoesNotExist from e
        return UnboundRemoteEngineAppInstanceRel(instance, self, self.store)


class RemotePlanMgr(BasePlanMgr):
    """Remote REST plans manager"""

    service_obj_cls = RemoteServiceObj

    def __init__(self, store: RemoteServiceStore):
        self.store = store
        self.service_mgr = RemoteServiceMgr(self.store)

    def list_plans(
        self, service: Optional[ServiceObj] = None, tenant_id: Optional[str] = None
    ) -> Generator[PlanObj, None, None]:
        for svc in self.service_mgr.list():
            if service and svc.uuid != service.uuid:
                continue
            plans = svc.get_plans(is_active=NOTSET)
            if tenant_id:
                plans = [plan for plan in plans if plan.tenant_id == tenant_id]
            yield from plans

    def create_plan(self, service: ServiceObj, plan_data: Dict):
        if not isinstance(service, RemoteServiceObj) or not service.supports_rest_upsert():
            raise UnsupportedOperationError("This service does not support the creation of plans.")

        plan_data["config"] = json.dumps(plan_data["config"])
        client = self._get_remote_client(service)
        client.create_plan(service_id=service.uuid, data=plan_data)
        # 更新 store 中的信息
        refresh_remote_service(self.store, service.uuid)

    def update_plan(self, service: ServiceObj, plan_id: str, plan_data: Dict):
        if not isinstance(service, RemoteServiceObj) or not service.supports_rest_upsert():
            raise UnsupportedOperationError("This service does not support the update of plans.")

        plan_data["config"] = json.dumps(plan_data["config"])
        client = self._get_remote_client(service)
        client.update_plan(service_id=service.uuid, plan_id=plan_id, data=plan_data)
        # 更新 store 中的信息
        refresh_remote_service(self.store, service.uuid)

    def delete_plan(self, service: ServiceObj, plan_id: str):
        raise UnsupportedOperationError("Remote Services does not support the deletion of plans.")

    def _get_remote_client(self, service: ServiceObj):
        remote_config = self.store.get_source_config(str(service.uuid))
        remote_client = RemoteServiceClient(remote_config)
        return remote_client


class RemoteServiceBinder:
    """Service binder for remote services"""

    def __init__(self, service: ServiceObj):
        self.service = service

    @atomic()
    def bind(self, module: Module, plan_id: str | None = None, env_plan_id_map: Dict[str, str] | None = None):
        """Create the binding relationship in local database.

        :raises BindServicePlanError: When no appropriate plans can be found.
        """
        svc_module_attachment, _ = RemoteServiceModuleAttachment.objects.get_or_create(
            module=module,
            service_id=self.service.uuid,
            defaults={"tenant_id": module.tenant_id},
        )

        # bind plans to each engineApp without creating
        for env in module.envs.all():
            try:
                plan = get_plan_by_env(self.service, env, plan_id, env_plan_id_map)
            except ValueError as e:
                raise BindServicePlanError(str(e))

            plan = cast(RemotePlanObj, plan)
            self._bind_for_env(env, plan)
        return svc_module_attachment

    @atomic()
    def bind_use_first_plan(self, module: Module):
        """Create the binding relationship in local database. Use the first plan
        if multiple plans are available.

        :raises BindServicePlanError: When no appropriate plans can be found.
        """
        svc_module_attachment, _ = RemoteServiceModuleAttachment.objects.get_or_create(
            module=module,
            service_id=self.service.uuid,
            defaults={"tenant_id": module.tenant_id},
        )

        # bind plans to each environment
        for env in module.envs.all():
            plans = PlanSelector().list(self.service, env)
            if not plans:
                raise BindServicePlanError(f"增强服务{self.service.name}方案未配置")

            # Use the first plan
            plan = cast(RemotePlanObj, plans[0])
            self._bind_for_env(env, plan)
        return svc_module_attachment

    @atomic()
    def bind_without_plan(self, module: Module):
        """bind the Service to Module, without binding any RemoteServiceEngineAppAttachment"""
        attachment, _ = RemoteServiceModuleAttachment.objects.get_or_create(
            service_id=self.service.uuid, module=module, defaults={"tenant_id": module.tenant_id}
        )
        return attachment

    def _bind_for_env(self, env: ModuleEnvironment, plan: RemotePlanObj):
        attachment, created = RemoteServiceEngineAppAttachment.objects.get_or_create(
            engine_app=env.engine_app,
            service_id=self.service.uuid,
            defaults={"plan_id": plan.uuid, "tenant_id": env.tenant_id},
        )

        if created or attachment.plan_id == constants.LEGACY_PLAN_ID:
            # 新创建的实例或者迁移实例不支持修改 plan
            return

        if attachment.service_instance_id is None:
            attachment.plan_id = plan.uuid
            attachment.save(update_fields=["plan_id"])
        else:
            # 已创建的实例不允许修改
            raise exceptions.CanNotModifyPlan(f"service {self.service.name} already provided")


class RemoteServiceInstanceMgr:
    """Remote REST service instance manager"""

    def __init__(self, store: RemoteServiceStore, service: RemoteServiceObj):
        self.store = store
        self.service_mgr = RemoteServiceMgr(self.store)
        self.service = service

    def get_instance_by_name(self, instance_name: str) -> str:
        service_id = str(self.service.uuid)
        client = self._get_remote_client(service_id=service_id)
        try:
            instance_data = client.retrieve_instance_by_name(service_id, instance_name)
        except Exception as e:
            raise exceptions.SvcInstanceNotFound(f"service instance {instance_name} not found") from e
        return instance_data.get("uuid")

    def _get_remote_client(self, service_id: str):
        remote_config = self.store.get_source_config(service_id)
        remote_client = RemoteServiceClient(remote_config)
        return remote_client


def get_app_by_instance_name(mgr: RemoteServiceInstanceMgr, instance_name: str) -> Optional[Application]:
    try:
        service_instance_id = mgr.get_instance_by_name(instance_name=instance_name)
    except exceptions.SvcInstanceNotFound:
        return None
    attachment = RemoteServiceEngineAppAttachment.objects.get(service_instance_id=service_instance_id)
    env = ApplicationEnvironment.objects.get(engine_app=attachment.engine_app)
    return env.application
