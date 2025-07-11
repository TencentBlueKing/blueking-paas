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

import datetime
import logging
import operator
import uuid
from typing import Callable, Dict, Generator, Iterable, Iterator, List, NamedTuple, Optional, TypeVar, cast

from attrs import define
from django.http import Http404

from paasng.accessories.servicehub.constants import ServiceBindingType, ServiceType
from paasng.accessories.servicehub.exceptions import (
    DuplicatedServiceBoundError,
    ServiceObjNotFound,
    SvcAttachmentDoesNotExist,
    UnboundSvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.local.manager import LocalPlanMgr, LocalServiceMgr, LocalServiceObj
from paasng.accessories.servicehub.models import (
    LocalServiceDBProperties,
    RemoteServiceDBProperties,
    ServiceDBProperties,
)
from paasng.accessories.servicehub.remote.manager import RemotePlanMgr, RemoteServiceMgr, RemoteServiceObj
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.accessories.servicehub.services import (
    EngineAppInstanceRel,
    PlanObj,
    ServiceObj,
    UnboundEngineAppInstanceRel,
)
from paasng.accessories.services.models import ServiceCategory
from paasng.core.region.models import set_service_categories_loader
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def _fetch_service_categories() -> List[ServiceCategory]:
    """Fetch service categories."""
    category_ids = {obj.category_id for obj in mixed_service_mgr.list_visible()}
    categories = ServiceCategory.objects.filter(pk__in=category_ids).order_by("-sort_priority")
    return list(categories)


set_service_categories_loader(_fetch_service_categories)


def _proxied_svc_dispatcher(method_name: str):
    """Dispatch a method call by service type"""

    def func(self, service: ServiceObj, *args, **kwargs):
        for mgr in self.mgr_instances:
            if isinstance(service, mgr.service_obj_cls):
                method = getattr(mgr, method_name)
                return method(service, *args, **kwargs)
        raise ValueError(f"{service} is an invalid service")

    return func


def _proxied_chained_generator(method_name: str):
    def func(self, *args, **kwargs):
        for mgr in self.mgr_instances:
            method = getattr(mgr, method_name)
            yield from method(*args, **kwargs)

    return func


class SharedServiceInfo(NamedTuple):
    """Shared service information object

    :param service: Shared service object
    :param module: Module which shares service from other modules
    :param ref_module: Module which was referenced(shared)
    """

    service: ServiceObj
    module: Module
    ref_module: Module


def get_db_properties(service: ServiceObj) -> ServiceDBProperties:
    """Get database properties object by service"""
    if isinstance(service, RemoteServiceObj):
        return RemoteServiceDBProperties()
    elif isinstance(service, LocalServiceObj):
        return LocalServiceDBProperties()
    raise ValueError(f"Unknown service obj type: {type(service)}")


def get_db_properties_by_service_type(service_type: str) -> ServiceDBProperties:
    """Get database properties object by service type"""
    if service_type == ServiceType.REMOTE:
        return RemoteServiceDBProperties()
    elif service_type == ServiceType.LOCAL:
        return LocalServiceDBProperties()
    raise ValueError(f"Unknown service type: {service_type}")


T = TypeVar("T", bound="MixedServiceMgr")


class MixedServiceMgr:
    """A hub for managing services of mixed sources: database and remote REST services"""

    def __init__(self):
        store = get_remote_store()
        self.mgr_instances = [LocalServiceMgr(), RemoteServiceMgr(store)]

    def get(self, uuid: str) -> ServiceObj:
        for mgr in self.mgr_instances:
            try:
                return mgr.get(uuid)
            except ServiceObjNotFound:
                continue
        raise ServiceObjNotFound(f"service with uuid {uuid} was not found")

    def find_by_name(self, name: str, include_invisible: bool = False) -> ServiceObj:
        for mgr in self.mgr_instances:
            try:
                obj = mgr.find_by_name(name)
                if include_invisible or obj.is_visible:
                    return obj
            except ServiceObjNotFound:
                continue
        raise ServiceObjNotFound(f"service with name {name} was not found")

    def get_or_404(self, *args, **kwargs) -> ServiceObj:
        """Get a ServiceObj object or raise 404

        :raises: Http404 if service was not found
        """
        try:
            return self.get(*args, **kwargs)
        except ServiceObjNotFound:
            raise Http404

    def get_module_rel(self, service_id: str, module_id: str):
        for mgr in self.mgr_instances:
            try:
                rel = mgr.get_module_rel(service_id=service_id, module_id=module_id)
            except SvcAttachmentDoesNotExist:
                # 由于 remote service 没有真正的建模，所以这里不容易直接判断是否真正存在，故略过
                logger.info(f"module<{module_id}> has no attachment with service<{service_id}>, try next mgr")
                continue
            else:
                return rel
        # 所有 mgr 都无法找到具体条目
        raise SvcAttachmentDoesNotExist(f"module<{module_id}> has no attachment with service<{service_id}>")

    def bind_service(
        self,
        service: ServiceObj,
        module: Module,
        plan_id: str | None = None,
        env_plan_id_map: Dict[str, str] | None = None,
    ) -> str:
        """Create bind relationship for given module and service object.

        Use this method when the user can manually select a plan to bind, if this
        condition is not met, use `bind_service_use_first_plan` instead.
        """
        DuplicatedBindingValidator(module, ServiceBindingType.NORMAL).validate(service)
        return _proxied_svc_dispatcher("bind_service")(
            self, service, module, plan_id=plan_id, env_plan_id_map=env_plan_id_map
        )

    def bind_service_use_first_plan(self, service: ServiceObj, module: Module) -> str:
        """Create bind relationship for given module and service object.

        The difference between this method and `bind_service` is that this method will
        use the first plan when multiple plans are available instead of raising an exception.
        """
        DuplicatedBindingValidator(module, ServiceBindingType.NORMAL).validate(service)
        return _proxied_svc_dispatcher("bind_service_use_first_plan")(self, service, module)

    # Dispatch via service type start

    get_attachment_by_instance_id = _proxied_svc_dispatcher("get_attachment_by_instance_id")
    get_instance_rel_by_instance_id = cast(
        Callable[..., EngineAppInstanceRel], _proxied_svc_dispatcher("get_instance_rel_by_instance_id")
    )
    get_provisioned_queryset = _proxied_svc_dispatcher("get_provisioned_queryset")
    get_provisioned_envs = _proxied_svc_dispatcher("get_provisioned_envs")
    module_is_bound_with = _proxied_svc_dispatcher("module_is_bound_with")
    update = _proxied_svc_dispatcher("update")
    destroy = _proxied_svc_dispatcher("destroy")

    # Dispatch via service type end

    # Proxied generator methods start

    list_by_category = _proxied_chained_generator("list_by_category")
    list_binded: Callable[..., Iterable["ServiceObj"]] = _proxied_chained_generator("list_binded")
    list_all_rels = cast(
        Callable[..., Generator[EngineAppInstanceRel, None, None]], _proxied_chained_generator("list_all_rels")
    )
    list_unprovisioned_rels = cast(
        Callable[..., Iterator[EngineAppInstanceRel]], _proxied_chained_generator("list_unprovisioned_rels")
    )
    list_provisioned_rels = cast(
        Callable[..., Iterable[EngineAppInstanceRel]], _proxied_chained_generator("list_provisioned_rels")
    )
    list = cast(Callable[..., Iterable[ServiceObj]], _proxied_chained_generator("list"))
    list_unbound_instance_rels = cast(
        Callable[..., Iterable[UnboundEngineAppInstanceRel]], _proxied_chained_generator("list_unbound_instance_rels")
    )
    list_visible = cast(Callable[..., Iterable[ServiceObj]], _proxied_chained_generator("list_visible"))

    # Proxied generator methods end

    def get_env_vars(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None, filter_enabled: bool = False
    ) -> Dict[str, str]:
        """Get all provisioned services env variables

        :param engine_app: EngineApp object
        :param service: Optional service object. if given, will only return credentials of the specified service,
            otherwise return the credentials of all services.
        :param filter_enabled: Whether to filter enabled service instances
        :returns: Dict of env variables.
        """
        groups = self.get_env_var_groups(engine_app, service=service, filter_enabled=filter_enabled)
        # 如果存在同名环境变量，以较新的为准
        groups.sort(key=operator.attrgetter("created_at"))

        result = {}
        for g in groups:
            result.update(g.data)
        return result

    def get_env_var_groups(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None, filter_enabled: bool = False
    ) -> "List[EnvVariableGroup]":
        """Get all provisioned services env variable groups. A group is a collection of environment variables
        that belong to a specific service instance.

        :param engine_app: EngineApp object
        :param service: Optional service object. if given, will only return credentials of the specified service,
            otherwise return the credentials of all services.
        :param filter_enabled: Whether to filter enabled service instances
        :returns: List of env variable groups.
        """
        results = []
        for rel in self.list_provisioned_rels(engine_app, service=service):
            if filter_enabled and not rel.db_obj.credentials_enabled:
                continue

            inst = rel.get_instance()
            results.append(
                EnvVariableGroup(service=rel.get_service(), data=inst.credentials, created_at=inst.create_time)
            )
        return results

    def get_attachment_by_engine_app(self, service: ServiceObj, engine_app: EngineApp):
        for mgr in self.mgr_instances:
            try:
                return mgr.get_attachment_by_engine_app(service, engine_app)
            except SvcAttachmentDoesNotExist:
                continue
        raise SvcAttachmentDoesNotExist(f"engine_app<{engine_app}> has no attachment with service<{service.uuid}>")

    def get_unbound_instance_rel_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        for mgr in self.mgr_instances:
            try:
                return mgr.get_unbound_instance_rel_by_instance_id(service, service_instance_id)
            except UnboundSvcAttachmentDoesNotExist:
                continue
        raise UnboundSvcAttachmentDoesNotExist(
            f"service<{service}> has no attachment with service_instance_id<{service_instance_id}>"
        )


class MixedPlanMgr:
    """A hub for managing plans of mixed sources: database and remote REST plans"""

    def __init__(self):
        store = get_remote_store()
        self.mgr_instances = [LocalPlanMgr(), RemotePlanMgr(store)]

    list = cast(Callable[..., Generator[PlanObj, None, None]], _proxied_chained_generator("list_plans"))
    create = _proxied_svc_dispatcher("create_plan")
    update = _proxied_svc_dispatcher("update_plan")
    delete = _proxied_svc_dispatcher("delete_plan")


mixed_service_mgr = MixedServiceMgr()
mixed_plan_mgr = MixedPlanMgr()


class DuplicatedBindingValidator:
    """Validate duplicated service bindings

    :param module: Module which is trying to create new binding relationship
    :param current_type: Type of current service binding
    """

    def __init__(self, module: Module, current_type: ServiceBindingType):
        self.module = module
        self.current_type = current_type

    def validate(self, service: ServiceObj) -> None:
        """Raise error when try to bind and share a service in the same time

        :raises: DuplicatedServiceBoundError when validation fails
        """
        if self.current_type == ServiceBindingType.NORMAL:
            self._check_duplicated_sharing(service)
        elif self.current_type == ServiceBindingType.SHARING:
            self._check_duplicated_normal(service)

    def _check_duplicated_normal(self, service: ServiceObj):
        if service in mixed_service_mgr.list_binded(self.module):
            raise DuplicatedServiceBoundError(f"Module: {self.module.name} already bound with service {service.name}")

    def _check_duplicated_sharing(self, service: ServiceObj):
        from .sharing import ServiceSharingManager

        infos = ServiceSharingManager(self.module).list_all_shared_info()
        for info in infos:
            if info.service == service:
                raise DuplicatedServiceBoundError(
                    f"Module: {self.module.name} already shared an attachment in service: {service.name}"
                )


@define
class EnvVariableGroup:
    """An env variable group.

    :param service: The owner service object.
    :param data: The environment variables.
    :param created_at: The time when the var group was created.
    """

    service: ServiceObj
    data: Dict[str, str]
    created_at: datetime.datetime | None
