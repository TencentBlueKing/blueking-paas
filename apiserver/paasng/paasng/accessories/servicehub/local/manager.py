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

"""Local services manager"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Iterable, Iterator, List, Optional, cast
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from paasng.accessories.servicehub import constants
from paasng.accessories.servicehub.binding_policy.selector import PlanSelector, get_plan_by_env
from paasng.accessories.servicehub.exceptions import (
    BindServicePlanError,
    CanNotModifyPlan,
    ProvisionInstanceError,
    ServiceObjNotFound,
    SvcAttachmentDoesNotExist,
    UnboundSvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.models import (
    ServiceEngineAppAttachment,
    ServiceModuleAttachment,
    UnboundServiceEngineAppAttachment,
)
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
from paasng.accessories.services.models import Plan, Service
from paasng.accessories.services.providers import get_plan_schema_by_provider_name
from paasng.misc.metrics import SERVICE_PROVISION_COUNTER
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


@dataclass
class LocalPlanObj(PlanObj):
    db_object: Plan = field(init=False)

    @classmethod
    def from_db(cls, plan: Plan) -> "LocalPlanObj":
        config = json.loads(plan.config or "{}")
        instance = cls(
            uuid=str(plan.uuid),
            tenant_id=plan.tenant_id,
            name=plan.name,
            description=plan.description,
            is_active=plan.is_active,
            is_eager=plan.is_eager,
            properties={},
            config=config,
        )
        instance.db_object = plan
        return instance


@dataclass()
class LocalServiceObj(ServiceObj):
    provider_name: str = ""
    db_object: Service = field(init=False)
    category_id = None
    category = None

    @classmethod
    def from_db_object(cls, service: Service) -> "LocalServiceObj":
        field_names = list(cls.__dataclass_fields__.keys())  # type: ignore
        fields = {k: getattr(service, k) for k in field_names if hasattr(service, k)}

        if service.logo_b64:
            fields["logo"] = service.logo_b64
        else:
            # Use the string url instead of the file-like object
            fields["logo"] = service.logo.url

        # format uuid instance to str
        if isinstance(fields["uuid"], UUID):
            fields["uuid"] = str(fields["uuid"])
        provider_name = service.config.get("provider_name", None)
        fields["provider_name"] = provider_name

        # plan schema
        if provider_name:
            fields["plan_schema"] = get_plan_schema_by_provider_name(provider_name)

        result = cls(**fields)
        result.db_object = service
        result.category_id = service.category_id
        result.category = service.category
        return result

    def get_plans(self, is_active=True) -> List[PlanObj]:
        qs = Plan.objects.filter(service=self.db_object)
        if is_active is not NOTSET:
            qs = qs.filter(is_active=is_active)
        return [LocalPlanObj.from_db(p).with_service(self) for p in qs]

    def get_plans_by_tenant_id(self, tenant_id: str, is_active=True) -> List["PlanObj"]:
        """Return all plans under the specified tenant"""
        all_plans = self.get_plans(is_active=is_active)
        return [plan for plan in all_plans if (plan.tenant_id == tenant_id)]


class LocalEngineAppInstanceRel(EngineAppInstanceRel):
    """A relationship between EngineApp and Provisioned instance"""

    def __init__(self, db_obj: ServiceEngineAppAttachment):
        self.db_obj = db_obj

    def get_service(self) -> LocalServiceObj:
        return LocalServiceObj.from_db_object(self.db_obj.service)

    def is_provisioned(self) -> bool:
        return self.db_obj.service_instance is not None

    def provision(self):
        """Provision a real service instance

        :raises: ProvisionInstanceError
        """
        if self.is_provisioned():
            logger.warning(f"local instance {self.db_obj.pk} already provisioned, skip")
            return

        try:
            self.db_obj.create_service_instance()
        except Exception as e:
            raise ProvisionInstanceError(
                _("配置资源实例异常: unable to provision instance for services<{service_name}>").format(
                    service_name=self.get_service().name
                )
            ) from e

        db_env = ModuleEnvironment.objects.get(engine_app=self.db_obj.engine_app)
        SERVICE_PROVISION_COUNTER.labels(
            environment=db_env.environment, service=self.db_obj.service.name, plan=self.db_obj.plan.name
        ).inc()

    def recycle_resource(self):
        service_instance = self.db_obj.service_instance
        self.db_obj.clean_service_instance()
        if self.db_obj.service.prefer_async_delete:
            UnboundServiceEngineAppAttachment.objects.create(
                owner=self.db_obj.owner,
                engine_app=self.db_obj.engine_app,
                service=self.db_obj.service,
                service_instance=service_instance,
                tenant_id=self.db_obj.tenant_id,
            )

    def get_instance(self) -> ServiceInstanceObj:
        """Get service instance object"""
        if not self.is_provisioned():
            raise ValueError("relationship is not provisioned yet")

        # All local service instance's credentials was prefixed with service name
        service_name = self.db_obj.service.name
        should_hidden_fields = constants.SERVICE_HIDDEN_FIELDS.get(service_name, [])
        should_remove_fields = constants.SERVICE_SENSITIVE_FIELDS.get(service_name, [])

        return ServiceInstanceObj(
            uuid=str(self.db_obj.service_instance_id),
            credentials=json.loads(self.db_obj.service_instance.credentials),
            config=self.db_obj.service_instance.config,
            tenant_id=self.db_obj.plan.tenant_id,
            should_hidden_fields=should_hidden_fields,
            should_remove_fields=should_remove_fields,
            create_time=self.db_obj.created,
        )

    def get_plan(self) -> LocalPlanObj:
        return LocalPlanObj.from_db(self.db_obj.plan)


class UnboundLocalEngineAppInstanceRel(UnboundEngineAppInstanceRel):
    """Unbound relationship between EngineApp and local provisioned instance"""

    def __init__(self, db_obj: UnboundServiceEngineAppAttachment):
        self.db_obj = db_obj

    def recycle_resource(self) -> None:
        self.db_obj.clean_service_instance()

    def get_instance(self) -> Optional[ServiceInstanceObj]:
        """Get service instance object"""
        # All local service instance's credentials was prefixed with service name
        service_name = self.db_obj.service.name
        should_hidden_fields = constants.SERVICE_HIDDEN_FIELDS.get(service_name, [])
        should_remove_fields = constants.SERVICE_SENSITIVE_FIELDS.get(service_name, [])

        return ServiceInstanceObj(
            uuid=str(self.db_obj.service_instance),
            credentials=json.loads(self.db_obj.service_instance.credentials),
            config=self.db_obj.service_instance.config,
            tenant_id=self.db_obj.service_instance.plan.tenant_id,
            should_hidden_fields=should_hidden_fields,
            should_remove_fields=should_remove_fields,
            create_time=self.db_obj.created,
        )


class LocalServiceMgr(BaseServiceMgr):
    """Local in-database services manager"""

    service_obj_cls = LocalServiceObj

    def get(self, uuid: str) -> LocalServiceObj:
        """Get a single service by given uuid

        :raises: ServiceObjNotFound
        """
        try:
            obj = Service.objects.get(uuid=uuid, is_active=True)
        except (Service.DoesNotExist, ValidationError) as e:
            raise ServiceObjNotFound(f"Service with id={uuid} not found in database") from e
        return LocalServiceObj.from_db_object(obj)

    def find_by_name(self, name: str) -> LocalServiceObj:
        """Find a single service by service name

        :raises: ServiceObjNotFound
        """
        try:
            obj = Service.objects.get(name=name, is_active=True)
        except Service.DoesNotExist as e:
            raise ServiceObjNotFound(f"Service with name={name} not found in database") from e
        return LocalServiceObj.from_db_object(obj)

    def list_by_category(self, category_id: int, include_hidden=False) -> Generator[ServiceObj, None, None]:
        """query a list of services by category"""
        services = Service.objects.filter(category=category_id, is_active=True)
        if not include_hidden:
            services = services.filter(is_visible=True)
        for svc in services:
            yield LocalServiceObj.from_db_object(svc)

    def list_visible(self) -> Iterable[ServiceObj]:
        """list all Services that is not hidden"""
        services = Service.objects.filter(is_active=True)
        for svc in services:
            if not svc.is_visible:
                continue
            yield LocalServiceObj.from_db_object(svc)

    def list(self) -> Iterable[ServiceObj]:
        """List all services"""
        services = Service.objects.filter(is_active=True)
        for svc in services:
            yield LocalServiceObj.from_db_object(svc)

    def _handle_service_data(self, data: Dict) -> Dict:
        """该方法负责将 ServiceObj 的数据格式转换成 in-database 的 Service 对象的存储格式"""
        # 丢弃 uuid 属性, 防止主键意外变更
        data.pop("uuid", None)
        # 由于本地增强服务并无 provider_name 等字段, 因此将这些额外属性存储在 config 字段中
        data.setdefault("config", {})
        for key, default in [("provider_name", None)]:  # type: ignore
            data["config"][key] = data.pop(key, default)
        # logo_64 直接存储 base64 格式的链接(也支持存储外链), 这里将 logo 重命名为 logo_b64, 以直接存储 base64 格式的图片
        data["logo_b64"] = data.pop("logo")
        return data

    def create(self, data: Dict):
        """create a local service"""
        data = self._handle_service_data(data)
        Service.objects.create(**data)

    def update(self, service: ServiceObj, data: Dict):
        """update the service"""
        db_obj = Service.objects.get(pk=service.uuid)
        data = self._handle_service_data(data)

        for key, value in data.items():
            setattr(db_obj, key, value)
        db_obj.save()

    def destroy(self, service: ServiceObj):
        """delete the service, and all plans and instances associated"""
        db_obj = Service.objects.get(pk=service.uuid)
        db_obj.delete()

    def bind_service(
        self,
        service: ServiceObj,
        module: Module,
        plan_id: str | None = None,
        env_plan_id_map: Dict[str, str] | None = None,
    ) -> str:
        """Bind a service to module"""
        db_service = Service.objects.get(pk=service.uuid)
        return LocalServiceBinder(LocalServiceObj.from_db_object(db_service)).bind(module, plan_id, env_plan_id_map).pk

    def bind_service_use_first_plan(self, service: ServiceObj, module: Module) -> str:
        """Bind a service to module, use the first plan when multiple plans are available"""
        db_service = Service.objects.get(pk=service.uuid)
        return LocalServiceBinder(LocalServiceObj.from_db_object(db_service)).bind_use_first_plan(module).pk

    def bind_service_partial(self, service: ServiceObj, module: Module) -> str:
        """Bind a service to module, without binding to engine app"""
        db_service = Service.objects.get(pk=service.uuid)
        return LocalServiceBinder(LocalServiceObj.from_db_object(db_service)).bind_without_plan(module).pk

    def list_binded(self, module: Module, category_id: Optional[int] = None) -> Iterator[ServiceObj]:
        """List module's bound services"""
        service_ids = map(
            str, ServiceModuleAttachment.objects.filter(module=module).values_list("service_id", flat=True)
        )
        for svc in Service.objects.filter(uuid__in=service_ids):
            obj = LocalServiceObj.from_db_object(svc)
            if category_id and category_id != obj.category_id:
                continue

            yield obj

    def list_all_rels(
        self, engine_app: EngineApp, service_id: Optional[str] = None
    ) -> Generator[LocalEngineAppInstanceRel, None, None]:
        """return all service attachment with engine_app"""
        qs = engine_app.service_attachment.all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        for attachment in qs:
            yield LocalEngineAppInstanceRel(attachment)

    def get_module_rel(self, service_id: str, module_id: str) -> Any:
        try:
            attachment = ServiceModuleAttachment.objects.get(module_id=module_id, service_id=service_id)
        except ServiceModuleAttachment.DoesNotExist:
            raise SvcAttachmentDoesNotExist("service attachment does not exist.")
        return attachment

    def list_unprovisioned_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[LocalEngineAppInstanceRel, None, None]:
        """Return all unprovisioned engine_app <-> local service instances by specified service (None for all)"""
        qs = engine_app.service_attachment.filter(service_instance__isnull=True)
        if service:
            qs = qs.filter(service_id=service.uuid)
        for attachment in qs:
            yield self.transform_rel_db_obj(attachment)

    def list_provisioned_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[LocalEngineAppInstanceRel, None, None]:
        """Return all provisioned engine_app <-> local service instances by specified service (None for all)"""
        qs = engine_app.service_attachment.exclude(service_instance__isnull=True)
        if service:
            qs = qs.filter(service_id=service.uuid)
        for attachment in qs:
            yield self.transform_rel_db_obj(attachment)

    def list_unbound_instance_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[UnboundEngineAppInstanceRel, None, None]:
        """Return all unbound local service instances, filter by specific service (None for all)"""
        qs = engine_app.unbound_service_attachment.all()
        if service:
            qs = qs.filter(service_id=service.uuid)
        for attachment in qs:
            yield UnboundLocalEngineAppInstanceRel(attachment)

    def get_attachment_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        try:
            return ServiceEngineAppAttachment.objects.get(
                service_id=service.uuid, service_instance__uuid=service_instance_id
            )
        except ServiceEngineAppAttachment.DoesNotExist as e:
            raise SvcAttachmentDoesNotExist from e

    def get_instance_rel_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        return self.transform_rel_db_obj(self.get_attachment_by_instance_id(service, service_instance_id))

    def get_provisioned_queryset(self, service: ServiceObj, application_ids: List[str]) -> QuerySet:
        """Return the queryset of provisioned db queryset by query condition"""
        modules = Module.objects.filter(application_id__in=application_ids)
        return ServiceModuleAttachment.objects.filter(service_id=service.uuid, module__in=modules)

    def transform_rel_db_obj(self, obj: ServiceEngineAppAttachment) -> LocalEngineAppInstanceRel:
        """Transform a db attachment to rel instance"""
        return LocalEngineAppInstanceRel(obj)

    def module_is_bound_with(self, service: ServiceObj, module: Module) -> bool:
        """Check if a module is bound with a service"""
        return ServiceModuleAttachment.objects.filter(module=module, service_id=service.uuid).exists()

    def get_provisioned_envs(self, service: ServiceObj, module: Module) -> List[AppEnvName]:
        """Get a list of bound envs"""
        env_list = []
        for env in module.get_envs():
            if ServiceEngineAppAttachment.objects.filter(
                engine_app=env.get_engine_app(), service__uuid=service.uuid, service_instance__isnull=False
            ).exists():
                env_list.append(env.environment)
        return env_list

    def get_attachment_by_engine_app(self, service: ServiceObj, engine_app: EngineApp):
        """Get ServiceEngineAppAttachment"""
        try:
            return ServiceEngineAppAttachment.objects.get(service_id=service.uuid, engine_app=engine_app)
        except ServiceEngineAppAttachment.DoesNotExist as e:
            raise SvcAttachmentDoesNotExist from e

    def get_unbound_instance_rel_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        """Return a unbound local service instance, filter by specific service and service instance id"""
        try:
            instance = UnboundServiceEngineAppAttachment.objects.get(
                service_id=service.uuid,
                service_instance__uuid=service_instance_id,
            )
        except UnboundServiceEngineAppAttachment.DoesNotExist as e:
            raise UnboundSvcAttachmentDoesNotExist from e
        return UnboundLocalEngineAppInstanceRel(instance)


class LocalPlanMgr(BasePlanMgr):
    """Local in-database plans manager"""

    service_obj_cls = LocalServiceObj

    def __init__(self):
        self.service_mgr = LocalServiceMgr()

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
        svc = self._get_service_in_db(service)

        plan_data = self._handle_plan_data(plan_data)
        Plan.objects.create(
            service=svc,
            name=plan_data["name"],
            description=plan_data["description"],
            is_active=plan_data["is_active"],
            config=plan_data["config"],
            tenant_id=plan_data["tenant_id"],
        )

    def update_plan(self, service: ServiceObj, plan_id: str, plan_data: Dict):
        svc = self._get_service_in_db(service)
        plan = get_object_or_404(Plan, pk=plan_id, service=svc)

        plan_data = self._handle_plan_data(plan_data)
        for k, v in plan_data.items():
            setattr(plan, k, v)

        plan.save()

    def delete_plan(self, service: ServiceObj, plan_id: str):
        svc = self._get_service_in_db(service)
        plan = svc.plan_set.get(pk=plan_id)
        plan.delete()

    def _get_service_in_db(self, service: ServiceObj):
        if not isinstance(service, LocalServiceObj):
            raise NotImplementedError

        svc = Service.objects.get(pk=service.uuid)
        return svc

    def _handle_plan_data(self, data: Dict) -> Dict:
        """该方法负责将 PlanObj 的数据格式转换成 in-database 的 Plan 对象的存储格式"""
        # 丢弃 uuid 属性, 防止主键意外变更
        data.pop("uuid", None)
        data.setdefault("config", {})
        # Plan 的 config 属性不是 JsonField, 因此需要 json.dumps
        data["config"] = json.dumps(data["config"])
        return data


class LocalPlainInstanceMgr(PlainInstanceMgr):
    """纯粹的本地增强服务实例的管理器, 不涉及增强服务资源申请的流程"""

    def __init__(self, db_obj: ServiceEngineAppAttachment):
        self.db_obj = db_obj

    def is_provisioned(self):
        return self.db_obj.service_instance is not None

    def create(self, credentials: Dict, config: Dict):
        """根据提供的 config, credentials 创建增强服务实例"""
        if self.is_provisioned():
            return

        self.db_obj.bind_service_instance(credentials=credentials, config=config)

    def destroy(self):
        """删除增强服务实例记录, 但不回收资源"""
        if not self.is_provisioned():
            return

        self.db_obj.unbind_service_instance()


class LocalServiceBinder:
    """Service binder for local services"""

    def __init__(self, service: LocalServiceObj):
        self.service = service

    @atomic()
    def bind(self, module: Module, plan_id: str | None, env_plan_id_map: dict[str, str] | None):
        """Create the binding relationship in local database.

        :raises BindServicePlanError: When no appropriate plans can be found.
        """
        svc_module_attachment, _ = ServiceModuleAttachment.objects.get_or_create(
            service=self.service.db_object, module=module, defaults={"tenant_id": module.tenant_id}
        )

        # bind plans to each environment
        for env in module.envs.all():
            try:
                plan = get_plan_by_env(self.service, env, plan_id, env_plan_id_map)
            except ValueError as e:
                raise BindServicePlanError(str(e))

            plan = cast(LocalPlanObj, plan)
            self._bind_for_env(env, plan)
        return svc_module_attachment

    @atomic()
    def bind_use_first_plan(self, module: Module):
        """Create the binding relationship in local database. Use the first plan
        if multiple plans are available.

        :raises BindServicePlanError: When no appropriate plans can be found.
        """
        svc_module_attachment, _ = ServiceModuleAttachment.objects.get_or_create(
            service=self.service.db_object, module=module, defaults={"tenant_id": module.tenant_id}
        )

        # bind plans to each environment
        for env in module.envs.all():
            plans = PlanSelector().list(self.service, env)
            if not plans:
                raise BindServicePlanError(f"增强服务{self.service.name}方案未配置")

            # Use the first plan
            plan = cast(LocalPlanObj, plans[0])
            self._bind_for_env(env, plan)
        return svc_module_attachment

    @atomic()
    def bind_without_plan(self, module: Module):
        """bind the Service to Module, without binding any ServiceEngineAppAttachment"""
        svc_module_attachment, _ = ServiceModuleAttachment.objects.get_or_create(
            service=self.service.db_object, module=module, defaults={"tenant_id": module.tenant_id}
        )
        return svc_module_attachment

    def _bind_for_env(self, env: ModuleEnvironment, plan: LocalPlanObj):
        svc_engine_app_attachment, created = ServiceEngineAppAttachment.objects.get_or_create(
            engine_app=env.engine_app,
            service=self.service.db_object,
            defaults={"plan": plan.db_object, "tenant_id": env.tenant_id},
        )

        if created or svc_engine_app_attachment.plan_id == constants.LEGACY_PLAN_ID:
            # 新创建的实例或者迁移实例不支持修改 plan
            return

        if svc_engine_app_attachment.service_instance_id is None:
            svc_engine_app_attachment.plan = plan.db_object
            svc_engine_app_attachment.save(update_fields=["plan"])
        else:
            # 已创建的实例不允许修改
            raise CanNotModifyPlan(f"service {self.service.name} already provided")
