# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""The universal services module, handles both services from database and remote REST API
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterator, List, Optional, cast

import arrow
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.networking.egress.shim import get_cluster_egress_info
from paasng.accessories.servicehub import constants, exceptions
from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment, RemoteServiceModuleAttachment
from paasng.accessories.servicehub.remote.client import RemoteServiceClient
from paasng.accessories.servicehub.remote.collector import RemoteSpecDefinitionUpdateSLZ, refresh_remote_service
from paasng.accessories.servicehub.remote.exceptions import (
    GetClusterEgressInfoError,
    ServiceNotFound,
    UnsupportedOperationError,
)
from paasng.accessories.servicehub.remote.store import RemoteServiceStore
from paasng.accessories.servicehub.services import (
    NOTSET,
    BasePlanMgr,
    BaseServiceMgr,
    EngineAppInstanceRel,
    ModuleSpecificationsHelper,
    PlainInstanceMgr,
    PlanObj,
    ServiceInstanceObj,
    ServiceObj,
    ServicePlansHelper,
    ServiceSpecificationDefinition,
    ServiceSpecificationHelper,
)
from paasng.accessories.services.models import ServiceCategory
from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.misc.metrics import SERVICE_PROVISION_COUNTER
from paasng.platform.applications.models import ModuleEnvironment
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

        parts = self.version.split('.')
        given_parts = version.split('.')
        for i, j in zip(parts, given_parts):
            if int(i) > int(j):
                return True
            if int(i) < int(j):
                return False
        return parts == given_parts


DEFAULT_META_INFO = MetaInfo(version=None)
VERSION_WITH_INST_CONFIG = '0.1.0'
VERSION_WITH_REST_UPSERT = '0.2.0'


@dataclass
class RemotePlanObj(PlanObj):
    @classmethod
    def from_data(cls, data: Dict):
        data.setdefault("is_active", True)
        properties = data.get("properties") or {}
        is_eager = data.pop("is_eager", False)
        region = data.pop("region", '')
        config = data.pop("config", {})
        return cls(
            is_eager=properties.get("is_eager", is_eager),
            region=properties.get("region", region),
            config=config,
            **data,
        )


@dataclass
class RemoteServiceObj(ServiceObj):
    plans: List[RemotePlanObj] = field(default_factory=list)
    meta_info: MetaInfo = DEFAULT_META_INFO

    _data = None
    category_id = None

    @classmethod
    def from_data(cls, service: Dict, region=None) -> 'RemoteServiceObj':
        field_names = list(cls.__dataclass_fields__.keys())  # type: ignore
        fields: Dict[str, Any] = {k: service.get(k) for k in field_names if k in service}
        fields['region'] = region

        fields['specifications'] = [ServiceSpecificationDefinition(**i) for i in fields.get('specifications') or ()]
        fields['plans'] = [RemotePlanObj.from_data(i) for i in fields.get('plans') or ()]

        # Set up meta info
        meta_info_data = service.get('_meta_info')
        if not meta_info_data:
            fields['meta_info'] = DEFAULT_META_INFO
        else:
            fields['meta_info'] = MetaInfo(version=meta_info_data['version'])

        result = cls(**fields)
        result._data = service
        result.category_id = service['category']
        return result

    @property
    def category(self):
        if not self._data:
            raise RuntimeError('RemoteServiceObj requires "_data" attribute')
        return ServiceCategory.objects.get(pk=self._data['category'])

    def get_plans(self, is_active=True) -> List['PlanObj']:
        return [plan.with_service(self) for plan in self.plans if (plan.is_active == is_active or is_active is NOTSET)]

    def supports_inst_config(self) -> bool:
        """Check if current service supports Feature: InstanceConfig"""
        return self.meta_info.semantic_version_gte(VERSION_WITH_INST_CONFIG)

    def supports_rest_upsert(self) -> bool:
        """Check if current service supports Feature: RestFul upsert Service/Plan"""
        return self.meta_info.semantic_version_gte(VERSION_WITH_REST_UPSERT)


@dataclass
class EnvClusterInfo:
    env: 'ModuleEnvironment'

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

    def __init__(self, db_obj: RemoteServiceEngineAppAttachment, mgr: 'RemoteServiceMgr', store: RemoteServiceStore):
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

        self.region = self.db_application.region

    def get_service(self) -> RemoteServiceObj:
        return self.mgr.get(str(self.db_obj.service_id), region=self.db_application.region)

    def is_provisioned(self) -> bool:
        return self.db_obj.service_instance_id is not None

    def provision(self):
        """Provision a real service instance

        :raises: ProvisionInstanceError
        """
        if self.is_provisioned():
            logger.warning(f'remote instance {self.db_obj.pk} already provisioned, skip')
            return

        if not self.remote_config.is_ready:
            logger.warning(f'remote service {self.get_service().name} is not ready, skip')
            return

        instance_id = str(uuid.uuid4())
        try:
            params = self.render_params(self.remote_config.provision_params_tmpl)
            self.remote_client.provision_instance(
                str(self.db_obj.service_id), str(self.db_obj.plan_id), instance_id, params=params
            )
        except Exception as e:
            logger.exception(f'Error provisioning new instance for {self.db_application.name}')
            raise exceptions.ProvisionInstanceError(
                _('配置资源实例异常: unable to provision instance for services<{service_name}>').format(
                    service_name=self.get_service().name
                )
            ) from e

        service_obj = self.get_service()

        # Write back to database
        self.db_obj.service_instance_id = instance_id
        self.db_obj.save(update_fields=['service_instance_id'])

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
            'app_id': str(self.db_application.id),
            'app_code': str(self.db_application.code),
            'app_name': str(self.db_application.name),
            'module': self.db_module.name,
            'environment': self.db_env.environment,
        }
        instance_id = self.db_obj.service_instance_id
        if not instance_id:
            raise ValueError('Relationship not provisioned, no instance_id can be found')

        try:
            self.remote_client.update_instance_config(instance_id, config={'paas_app_info': paas_app_info})
        except Exception:
            logger.exception(f'Error when updating instance config for {instance_id}')

    def recycle_resource(self):
        """对于 remote service 我们默认其已经具备了回收的能力"""
        if self.is_provisioned():
            try:
                self.remote_client.delete_instance(instance_id=str(self.db_obj.service_instance_id))
            except Exception as e:
                logger.exception("Error occurs during recycling")
                raise exceptions.SvcInstanceDeleteError("unable to delete instance") from e
        self.db_obj.service_instance_id = None
        self.db_obj.save()

    def get_instance(self) -> ServiceInstanceObj:
        """Get service instance object"""
        if not self.is_provisioned():
            raise ValueError('relationship is not provisioned yet')

        # TODO: failure tolerance
        instance_data = self.remote_client.retrieve_instance(str(self.db_obj.service_instance_id))
        # TODO: More data validations
        if not instance_data.get('uuid') == str(self.db_obj.service_instance_id):
            raise exceptions.SvcInstanceNotAvailableError('uuid in data does not match')

        svc_obj = self.get_service()
        create_time = arrow.get(instance_data.get('created'))  # type: ignore
        return create_svc_instance_obj_from_remote(
            uuid=str(self.db_obj.service_instance_id),
            credentials=instance_data['credentials'],
            config=instance_data['config'],
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
        if 'bk_monitor_space_id' in params_tmpl:
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

        svc_data = self.store.get(str(self.db_obj.service_id), region=self.db_application.region)
        for d in svc_data['plans']:
            if d["uuid"] == plan_id:
                return RemotePlanObj.from_data(d)

        raise RuntimeError('Plan not found')


class RemotePlainInstanceMgr(PlainInstanceMgr):
    """纯粹的远程增强服务实例的管理器, 仅调用远程接口创建增强服务实例, 不涉及增强服务资源申请的流程"""

    def __init__(self, db_obj: RemoteServiceEngineAppAttachment, mgr: 'RemoteServiceMgr'):
        self.mgr = mgr
        # Database objects
        self.db_obj = db_obj
        self.db_env = ModuleEnvironment.objects.get(engine_app=self.db_obj.engine_app)
        self.db_engine_app = self.db_obj.engine_app
        self.db_application = self.db_env.application
        self.db_module = self.db_env.module

        self.remote_client = self.get_remote_client()

    def get_service(self) -> RemoteServiceObj:
        return self.mgr.get(str(self.db_obj.service_id), region=self.db_application.region)

    def get_remote_client(self):
        remote_config = self.mgr.store.get_source_config(str(self.db_obj.service_id))
        remote_client = RemoteServiceClient(remote_config)
        return remote_client

    def sync_instance_config(self):
        """Sync instance config with remote service"""
        paas_app_info: Dict[str, str] = {
            'app_id': str(self.db_application.id),
            'app_code': str(self.db_application.code),
            'app_name': str(self.db_application.name),
            'module': self.db_module.name,
            'environment': self.db_env.environment,
        }
        instance_id = self.db_obj.service_instance_id
        if not instance_id:
            raise ValueError('Relationship not provisioned, no instance_id can be found')

        try:
            self.remote_client.update_instance_config(str(instance_id), config={'paas_app_info': paas_app_info})
        except Exception:
            logger.exception(f'Error when updating instance config for {instance_id}')

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
            logger.exception(f'Error bind instance for {self.db_application.name}')
            raise exceptions.BaseServicesException(
                _('绑定实例异常: unable to provision instance for services<{service_obj_name}>').format(
                    service_obj_name=service_obj.name
                )
            ) from e

        # Write back to database
        self.db_obj.service_instance_id = instance_id
        self.db_obj.save(update_fields=['service_instance_id', 'updated'])

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
    uuid: str, credentials: Dict, config: Dict, field_prefix: str, create_time: 'datetime.datetime'
) -> ServiceInstanceObj:
    """Create a Service Instance object for remote service

    special fields:

    - `config.__meta__`: if "should_hidden_fields" or "should_remove_fields" was included in this
        field, the value will be popped for instance intializing.
    """

    def _format_key(val):
        """Turn credential keys in to upper case and with prefix"""
        return f'{field_prefix}_{val}'.upper()

    _credentials = {_format_key(key): value for key, value in credentials.items()}

    # Parse and process meta configs
    meta_config = config.pop('__meta__', {})
    should_hidden_fields = list(map(_format_key, meta_config.get('should_hidden_fields', [])))
    should_remove_fields = list(map(_format_key, meta_config.get('should_remove_fields', [])))
    return ServiceInstanceObj(uuid, _credentials, config, should_hidden_fields, should_remove_fields, create_time)


class RemoteServiceMgr(BaseServiceMgr):
    """Remote REST services manager"""

    service_obj_cls = RemoteServiceObj

    def __init__(self, store: RemoteServiceStore):
        self.store = store

    def get(self, uuid: str, region: str) -> RemoteServiceObj:
        """Get a single service by given uuid

        :raises: ServiceObjNotFound
        """
        try:
            obj = self.store.get(uuid, region)
        except (ServiceNotFound, RuntimeError) as e:
            raise exceptions.ServiceObjNotFound(f'Service with id={uuid} not found in remote') from e
        return RemoteServiceObj.from_data(obj, region=region)

    def find_by_name(self, name: str, region: str) -> RemoteServiceObj:
        """Find a single service by service name

        :raises: ServiceObjNotFound
        """
        objs = self.store.filter(region, conditions={"name": name})
        if not objs:
            raise exceptions.ServiceObjNotFound(f'Service with name={name} not found in remote')
        # Use the first matched services objects
        return RemoteServiceObj.from_data(objs[0], region=region)

    def list_by_category(
        self, region: str, category_id: int, include_hidden=False
    ) -> Generator[ServiceObj, None, None]:
        """query a list of services by category"""
        items = self.store.filter(region, conditions={"category": category_id})
        for svc in items:
            obj = RemoteServiceObj.from_data(svc, region=region)
            # Ignore services which is_visible field is False
            if not include_hidden and not svc['is_visible']:
                continue
            yield obj

    def list_by_region(self, region: str, include_hidden=False) -> Generator[ServiceObj, None, None]:
        """query a list of services by region"""
        items = self.store.filter(region)
        for svc in items:
            # Ignore services which is_visible field is False
            if not include_hidden and not svc['is_visible']:
                continue

            yield RemoteServiceObj.from_data(svc, region=region)

    def list(self) -> Generator[ServiceObj, None, None]:
        """query all list of services"""
        items = self.store.all()
        for svc in items:
            yield RemoteServiceObj.from_data(svc, region=None)

    def _handle_service_data(self, data: Dict) -> Dict:
        # 由于远程增强服务在存储 category_id 的字段命名为 category, 因此这里需要做个重命名
        data["category"] = data.pop("category_id")

        # 远程增强服务的 specification 中的 display_name 是 TranslatedField
        # 但本地增强服务并无 specification 字段, 仅将这些额外属性存储在 config 字段中
        # specification.displayname 的国际化目前是由前端来处理
        data['specifications'] = RemoteSpecDefinitionUpdateSLZ(data['specifications'], many=True).data
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
        attachments = RemoteServiceModuleAttachment.objects.filter(module=module).values('service_id')
        service_ids = [str(obj['service_id']) for obj in attachments]
        for svc in self.store.bulk_get(service_ids, region=module.region):
            if svc:
                obj = RemoteServiceObj.from_data(svc, region=module.region)
                if category_id and category_id != obj.category_id:
                    continue
                yield obj

    def bind_service(self, service: ServiceObj, module: Module, specs: Optional[Dict[str, str]] = None) -> str:
        """Bind a service to module"""
        helper = ModuleSpecificationsHelper(service=service, module=module, specs=specs or {})
        helper.fill_protected_specs()

        binder = RemoteServiceBinder(service)
        return binder.bind(module, helper.specs).pk

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

    def get_provisioned_queryset_by_services(self, services: List[ServiceObj], application_ids: List[str]) -> QuerySet:
        modules = Module.objects.filter(application_id__in=application_ids)
        return RemoteServiceModuleAttachment.objects.filter(
            service_id__in=[service.uuid for service in services],
            module__in=modules,
        )

    def transform_rel_db_obj(self, obj: RemoteServiceEngineAppAttachment) -> RemoteEngineAppInstanceRel:
        """Transform a db attachment to rel instance"""
        return RemoteEngineAppInstanceRel(obj, self, self.store)

    def module_is_bound_with(self, service: ServiceObj, module: Module) -> bool:
        """Check if a module is bound with a service"""
        return RemoteServiceModuleAttachment.objects.filter(module=module, service_id=service.uuid).exists()

    def get_provisioned_envs(self, service: ServiceObj, module: Module) -> List['AppEnvName']:
        """Get a list of bound envs"""
        env_list = []
        for env in module.get_envs():
            if RemoteServiceEngineAppAttachment.objects.filter(
                engine_app=env.get_engine_app(), service=service, service_instance__isnull=True
            ).exists():
                env_list.append(env.environment)
        return env_list


class RemotePlanMgr(BasePlanMgr):
    """Remote REST plans manager"""

    service_obj_cls = RemoteServiceObj

    def __init__(self, store: RemoteServiceStore):
        self.store = store
        self.service_mgr = RemoteServiceMgr(self.store)

    def list_plans(self, service: Optional[ServiceObj] = None) -> Generator[PlanObj, None, None]:
        for svc in self.service_mgr.list():
            if service and svc.uuid != service.uuid:
                continue

            yield from svc.get_plans(is_active=NOTSET)

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
    def bind(self, module: Module, specs: Optional[Dict[str, str]] = None):
        """Create the binding relationship in local database"""
        specs_helper = ServiceSpecificationHelper(
            self.service.specifications,
            list(ServicePlansHelper.from_service(self.service).get_by_region(module.region)),
        )
        plans = specs_helper.filter_plans(specs)

        svc_module_attachment, _ = RemoteServiceModuleAttachment.objects.get_or_create(
            module=module,
            service_id=self.service.uuid,
        )

        # bind plans to each engineApp without creating
        for env in module.envs.all():  # type: ModuleEnvironment
            plan = cast(RemotePlanObj, self._get_plan_by_env(env, plans))
            self._bind_for_env(env, plan)
        return svc_module_attachment

    @atomic()
    def bind_without_plan(self, module: Module):
        """bind the Service to Module, without binding any RemoteServiceEngineAppAttachment"""
        attachment, _ = RemoteServiceModuleAttachment.objects.get_or_create(
            service_id=self.service.uuid, module=module
        )
        return attachment

    @staticmethod
    def _get_plan_by_env(env: ModuleEnvironment, plans: List[PlanObj]) -> PlanObj:
        """Return the first plan which matching the given env."""
        plans = sorted(plans, key=lambda i: ('restricted_envs' in i.properties), reverse=True)

        for plan in plans:
            if 'restricted_envs' not in plan.properties or env.environment in plan.properties['restricted_envs']:
                return plan
        else:
            raise RuntimeError("can not bind a plan")

    def _bind_for_env(self, env: ModuleEnvironment, plan: RemotePlanObj):
        attachment, created = RemoteServiceEngineAppAttachment.objects.get_or_create(
            engine_app=env.engine_app,
            service_id=self.service.uuid,
            defaults={"plan_id": plan.uuid},
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
