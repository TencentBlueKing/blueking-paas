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

import logging
import uuid
import weakref
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterator, List, Optional, Type

from django.db.models import QuerySet

from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    import datetime

logger = logging.getLogger(__name__)

NOTSET = object()


@dataclass
class ServiceObj:
    """A universal service object"""

    uuid: str
    name: str
    logo: str = field(compare=False)
    is_visible: bool
    is_active: bool = True
    available_languages: str = ""
    config: Dict = field(default_factory=dict, compare=False)
    plan_schema: Dict = field(default_factory=dict, compare=False)

    display_name: str = ""
    description: str = ""
    long_description: str = ""
    instance_tutorial: str = ""

    # below attributes should be set by subclass
    category_id = None
    category = None

    def get_plans(self, is_active=True) -> List["PlanObj"]:
        """Return all related plans"""
        raise NotImplementedError()

    def get_plans_by_tenant_id(self, tenant_id: str, is_active=True) -> List["PlanObj"]:
        """Return all plans under the specified tenant"""
        raise NotImplementedError()


@dataclass
class PlanObj:
    """A universal plan object"""

    uuid: str
    name: str
    tenant_id: str
    description: str
    is_active: bool
    is_eager: bool
    properties: Dict
    config: Dict = field(default_factory=dict)

    def with_service(self, service: ServiceObj):
        """Lazy connect to service, avoid circular dependency"""
        self._service = weakref.ref(service)
        return self

    @property
    def service(self) -> Optional[ServiceObj]:
        if hasattr(self, "_service"):
            return self._service()
        return None


class ServiceInstanceObj:
    """A universal Service Instance object"""

    def __init__(
        self,
        uuid: str,
        credentials: Dict,
        config: Dict,
        tenant_id: str,
        should_hidden_fields: Optional[List] = None,
        should_remove_fields: Optional[List] = None,
        create_time: Optional["datetime.datetime"] = None,
    ):
        self.uuid = uuid
        self._credentials = credentials
        self._config = config
        self.tenant_id = tenant_id
        self.should_hidden_fields = should_hidden_fields or []
        self.should_remove_fields = should_remove_fields or []
        self.create_time = create_time

    def get_credentials(self, include_all: bool = True):
        """Return the credentials

        :param include_all: if False, will ignore all hidden/remove values
        """
        if include_all:
            return self._credentials

        result = OrderedDict()
        for key, value in self._credentials.items():
            if not (key in self.should_hidden_fields or key in self.should_remove_fields):
                result[key] = value
        return result

    @property
    def credentials(self):
        return self.get_credentials(include_all=True)

    @property
    def credentials_insensitive(self):
        return self.get_credentials(include_all=False)

    @property
    def config(self):
        return self._config

    def get_hidden_credentials(self):
        return {key: self._credentials[key] for key in self.should_hidden_fields if key in self._credentials}


class EngineAppInstanceRel(metaclass=ABCMeta):
    """A relationship between EngineApp and Provinsioned instance"""

    db_obj: Any

    @abstractmethod
    def get_service(self) -> ServiceObj:
        raise NotImplementedError

    @abstractmethod
    def is_provisioned(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def provision(self):
        raise NotImplementedError

    @abstractmethod
    def get_instance(self) -> ServiceInstanceObj:
        raise NotImplementedError

    @abstractmethod
    def get_plan(self) -> PlanObj:
        raise NotImplementedError

    def delete(self):
        """include delete rel, real resource recycle. If prefer asynchronous delete, add a unbound attachment record."""
        if self.is_provisioned():
            self.recycle_resource()
        logger.info("going to delete remote service attachment from db")
        # delete rel itself from real db
        self.db_obj.delete()

    @abstractmethod
    def recycle_resource(self):
        """Recycle resources but do not unbind the service"""
        raise NotImplementedError


class UnboundEngineAppInstanceRel(metaclass=ABCMeta):
    """A provinsioned instance which is unbound with engine app"""

    db_obj: Any

    @abstractmethod
    def get_instance(self) -> Optional[ServiceInstanceObj]:
        raise NotImplementedError

    @abstractmethod
    def recycle_resource(self):
        """Recycle resources"""
        raise NotImplementedError


class PlainInstanceMgr(metaclass=ABCMeta):
    """纯粹的增强服务实例的管理器, 不涉及增强服务资源申请的流程"""

    db_obj: Any

    @abstractmethod
    def is_provisioned(self) -> bool:
        raise NotImplementedError

    def create(self, credentials: Dict, config: Dict):
        """根据提供的 config, credentials 创建增强服务实例"""
        raise NotImplementedError

    def destroy(self):
        """删除增强服务实例记录, 但不回收资源"""
        raise NotImplementedError


class BaseServiceMgr(metaclass=ABCMeta):
    """Base class for service manager"""

    service_obj_cls = ServiceObj

    @abstractmethod
    def list_by_category(self, category_id: int, include_hidden: bool = False) -> Generator[ServiceObj, None, None]:
        raise NotImplementedError

    @abstractmethod
    def list_binded(self, module: Module, category_id: Optional[int] = None) -> Iterator[ServiceObj]:
        raise NotImplementedError

    @abstractmethod
    def module_is_bound_with(self, service: ServiceObj, module: Module) -> bool:
        """Check if a module is bound with a service"""
        raise NotImplementedError

    @abstractmethod
    def bind_service(
        self,
        service: ServiceObj,
        module: Module,
        plan_id: str | None = None,
        env_plan_id_map: Dict[str, str] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def bind_service_use_first_plan(self, service: ServiceObj, module: Module) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_unprovisioned_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[EngineAppInstanceRel, None, None]:
        raise NotImplementedError

    @abstractmethod
    def list_provisioned_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[EngineAppInstanceRel, None, None]:
        raise NotImplementedError

    @abstractmethod
    def list_unbound_instance_rels(
        self, engine_app: EngineApp, service: Optional[ServiceObj] = None
    ) -> Generator[UnboundEngineAppInstanceRel, None, None]:
        raise NotImplementedError

    @abstractmethod
    def get_provisioned_queryset(self, service: ServiceObj, application_ids: List[str]) -> QuerySet:
        raise NotImplementedError

    @abstractmethod
    def get_attachment_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        raise NotImplementedError

    @abstractmethod
    def get_module_rel(self, service_id: str, module_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get(self, uuid) -> ServiceObj:
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> ServiceObj:
        raise NotImplementedError

    @abstractmethod
    def get_attachment_by_engine_app(self, service: ServiceObj, engine_app: EngineApp):
        raise NotImplementedError

    @abstractmethod
    def get_unbound_instance_rel_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        raise NotImplementedError


class BasePlanMgr:
    """Base class for plan manager"""

    service_obj_cls: Type[ServiceObj]

    def list_plans(
        self, service: Optional[ServiceObj] = None, tenant_id: Optional[str] = None
    ) -> Generator[PlanObj, None, None]:
        raise NotImplementedError

    def create_plan(self, service: ServiceObj, plan_data: Dict):
        raise NotImplementedError

    def update_plan(self, service: ServiceObj, plan_id: str, plan_data: Dict):
        raise NotImplementedError

    def delete_plan(self, service: ServiceObj, plan_id: str):
        raise NotImplementedError
