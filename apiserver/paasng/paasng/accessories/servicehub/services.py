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
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterable, Iterator, List, Mapping, Optional, Type

from django.conf import settings
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.shim import get_application_cluster
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    import datetime

logger = logging.getLogger(__name__)


@dataclass
class ServiceSpecificationDefinition:
    """Service spec definition"""

    name: str
    description: str
    recommended_value: Optional[str] = None
    is_public: Optional[bool] = field(default=None)
    display_name: str = ""

    def __post_init__(self):
        # 规格定义是否需要暴露给用户
        if self.is_public is None:
            self.is_public = self.name not in settings.SERVICE_PROTECTED_SPEC_NAMES
        self.description = _(self.description)
        self.display_name = _(self.display_name)

    def as_dict(self) -> Dict:
        return asdict(self)


NOTSET = object()


@dataclass
class ServiceObj:
    """A universal service object"""

    region: str
    uuid: str
    name: str
    logo: str = field(compare=False)
    is_visible: bool
    is_active: bool = True
    available_languages: str = ""
    config: Dict = field(default_factory=dict, compare=False)
    specifications: List["ServiceSpecificationDefinition"] = field(default_factory=list, compare=False)

    display_name: str = ""
    description: str = ""
    long_description: str = ""
    instance_tutorial: str = ""

    # below attributes should be set by subclass
    category_id = None
    category = None

    @property
    def public_specifications(self) -> List["ServiceSpecificationDefinition"]:
        return [i for i in self.specifications if i.is_public]

    @property
    def protected_specifications(self) -> List["ServiceSpecificationDefinition"]:
        return [i for i in self.specifications if not i.is_public]

    def get_plans(self, is_active=True) -> List["PlanObj"]:
        """Return all related plans"""
        raise NotImplementedError()


@dataclass
class PlanObj:
    """A universal plan object"""

    uuid: str
    name: str
    description: str
    is_active: bool
    is_eager: bool
    region: str
    specifications: Dict[str, str]
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
        should_hidden_fields: Optional[List] = None,
        should_remove_fields: Optional[List] = None,
        create_time: Optional["datetime.datetime"] = None,
    ):
        self.uuid = uuid
        self._credentials = credentials
        self._config = config
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
        """include delete rel, mark_unbound & real resource recycle"""
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
    def get_instance(self) -> ServiceInstanceObj:
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
    def list_by_category(
        self, region: str, category_id: int, include_hidden: bool = False
    ) -> Generator[ServiceObj, None, None]:
        raise NotImplementedError

    @abstractmethod
    def list_binded(self, module: Module, category_id: Optional[int] = None) -> Iterator[ServiceObj]:
        raise NotImplementedError

    @abstractmethod
    def module_is_bound_with(self, service: ServiceObj, module: Module) -> bool:
        """Check if a module is bound with a service"""
        raise NotImplementedError

    @abstractmethod
    def bind_service(self, service: ServiceObj, module: Module, specs: Optional[Dict[str, str]] = None) -> str:
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
    def get_provisioned_queryset_by_services(self, services: List[ServiceObj], application_ids: List[str]) -> QuerySet:
        raise NotImplementedError

    @abstractmethod
    def get_attachment_by_instance_id(self, service: ServiceObj, service_instance_id: uuid.UUID):
        raise NotImplementedError

    @abstractmethod
    def get_module_rel(self, service_id: str, module_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get(self, uuid: str, region: str) -> ServiceObj:
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str, region: str) -> ServiceObj:
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

    def list_plans(self, service: Optional[ServiceObj] = None) -> Generator[PlanObj, None, None]:
        raise NotImplementedError

    def create_plan(self, service: ServiceObj, plan_data: Dict):
        raise NotImplementedError

    def update_plan(self, service: ServiceObj, plan_id: str, plan_data: Dict):
        raise NotImplementedError

    def delete_plan(self, service: ServiceObj, plan_id: str):
        raise NotImplementedError


@dataclass
class ServicePlansHelper:
    """Hepler work for plans"""

    plans: List["PlanObj"]

    @classmethod
    def from_service(cls, service: "ServiceObj") -> "ServicePlansHelper":
        return cls(service.get_plans())

    def get_by_region(self, region: "str") -> "Iterable[PlanObj]":
        """"""
        for p in self.plans:
            if p.region == region:
                yield p


@dataclass
class ServiceSpecificationHelper:
    """Helper work for service specifications"""

    definitions: List["ServiceSpecificationDefinition"]
    plans: List["PlanObj"]

    def __post_init__(self):
        specification_keys = {definition.name for definition in self.definitions}
        if len(specification_keys) != len(self.definitions):
            raise ValueError("Encountered duplicate field name.")

    @classmethod
    def from_service(cls, service: "ServiceObj") -> "ServiceSpecificationHelper":
        return cls(definitions=service.specifications, plans=service.get_plans())

    @classmethod
    def from_service_public_specifications(cls, service: "ServiceObj") -> "ServiceSpecificationHelper":
        return cls(definitions=service.public_specifications, plans=service.get_plans())

    @classmethod
    def from_service_protected_specifications(cls, service: "ServiceObj") -> "ServiceSpecificationHelper":
        return cls(definitions=service.protected_specifications, plans=service.get_plans())

    def filter_plans(self, specifications: Optional[Dict] = None) -> List["PlanObj"]:
        """Get plans which matched specifications. But if not provided any specifications, return all plans."""
        plans = self.plans
        if not specifications:
            return plans

        results = []
        target_specs = self._sanitize_specs(specifications)
        for plan in plans:
            plan_specs = self._sanitize_specs(plan.specifications)
            for k, v in target_specs.items():
                if v is not None and plan_specs[k] != v:
                    break
            else:
                results.append(plan)
        return results

    def get_recommended_spec(self) -> Dict[str, Optional[str]]:
        """Get recommended specs."""
        recommended_spec = {}
        grouped_spec_values: Optional[Dict] = self.get_grouped_spec_values()
        for definition in self.definitions:
            value = definition.recommended_value
            if grouped_spec_values is None:
                value = None
            elif value in grouped_spec_values:
                grouped_spec_values = grouped_spec_values.get(value)
            else:
                value = grouped_spec_values = None
            recommended_spec[definition.name] = value
        return self._sanitize_specs(recommended_spec)

    def list_plans_spec_value(self) -> List[List[Optional[str]]]:
        """List spec_value from plans.

        :return: [plan_A_spec_value, plan_B_spec_value, ...]
        """
        if not self.definitions:
            return []

        plan_spec_values = []
        for plan in self.plans:
            plan_spec_values.append(list(self._sanitize_specs(plan.specifications).values()))
        return plan_spec_values

    def get_grouped_spec_values(self) -> Dict:
        """Get grouped spec_values from plan."""
        return self.parse_spec_values_tree(self.list_plans_spec_value())

    def _sanitize_specs(self, specs: Mapping[str, Optional[str]]) -> Dict[str, Optional[str]]:
        """Order given specs by service definitions, and ignored those undefined specs."""
        return OrderedDict((definition.name, specs.get(definition.name)) for definition in self.definitions)

    @staticmethod
    def parse_spec_values_tree(values: List[List[Optional[str]]]) -> Dict:
        """Parse grouped specs from given specs.

        >>> ServiceSpecificationHelper.parse_spec_values_tree([["a", "b"], ["a", "c"]])
        {'a': {'b': None, 'c': None}}

        >>> ServiceSpecificationHelper.parse_spec_values_tree([["a", "b"], ["a", "c"], ["d", "c"]])
        {'a': {'b': None, 'c': None}, 'd': {'c': None}}

        >>> ServiceSpecificationHelper.parse_spec_values_tree([["a", "b", "c", "e"], ["d"]])
        {'a': {'b': {'c': {'e': None}}}, "d": None}

        >>> ServiceSpecificationHelper.parse_spec_values_tree([["a", "b"], ["a", None]])
        {'a': {'b': None, None: None}}

        :param values: given plans spec values, grouped by List.
        :return: grouped dict.
        """
        specifications: Dict = {}
        for sub_specs in values:
            current = specifications
            for spec in sub_specs[:-1]:
                current = current.setdefault(spec, {})

            tail = sub_specs[-1]
            current[tail] = None  # mark end
        return specifications

    def format_given_specs(self, specs: Dict[str, str]) -> List[Dict]:
        """Format given specs dict by definitions."""
        results = []
        for definition in self.definitions:
            if definition.name not in specs:  # ignore undefined key.
                continue

            results.append(
                {
                    "name": definition.name,
                    "display_name": definition.display_name,
                    "description": definition.description,
                    "is_public": definition.is_public,
                    "value": specs[definition.name],
                }
            )
        return results


@dataclass
class ModuleSpecificationsHelper:
    service: "ServiceObj"
    module: "Module"
    specs: Dict[str, str]

    def __post_init__(self):
        if self.specs is None:
            self.specs = {}

    def fill_spec_app_zone(self):
        cluster_info = get_application_cluster(self.module.application)
        self.specs["app_zone"] = settings.APP_ZONE_CLUSTER_MAPPINGS.get(cluster_info.name, "universal")

    def fill_protected_specs(self):
        for name in settings.SERVICE_PROTECTED_SPEC_NAMES:
            method = getattr(self, f"fill_spec_{name}", None)
            if callable(method):
                method()
