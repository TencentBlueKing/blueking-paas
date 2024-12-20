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
import abc
from typing import Any

from attrs import define

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceBindingPolicyType,
)
from paasng.accessories.servicehub.manager import get_db_properties
from paasng.accessories.servicehub.services import ServiceObj
from paasng.platform.applications.models import ModuleEnvironment


def binding_policy_factory(type_: str, data: dict[str, Any]) -> "BindingPolicy":
    """Create a binding policy object"""
    match type_:
        case ServiceBindingPolicyType.STATIC.value:
            return StaticBindingPolicy(data=data)
        case ServiceBindingPolicyType.ENV_SPECIFIC.value:
            return EnvSpecificBindingPolicy(data=data)
        case _:
            raise ValueError(f"Invalid type: {type_}")


class BindingPolicy(abc.ABC):
    """The base type for the binding policy"""

    @abc.abstractmethod
    def get_plan_ids(self, env: ModuleEnvironment) -> list[str]:
        raise NotImplementedError


@define
class StaticBindingPolicy(BindingPolicy):
    """The static binding policy type.

    :param data: policy data which contains plan ids.
    """

    data: dict[str, Any]

    def get_plan_ids(self, env: ModuleEnvironment) -> list[str]:
        """Get the configured plan ids"""
        return self.data["plan_ids"]


@define
class EnvSpecificBindingPolicy(BindingPolicy):
    """The environment specific binding policy type.

    :param data: policy data which contains plan ids.
    """

    data: dict[str, Any]

    def get_plan_ids(self, env: ModuleEnvironment) -> list[str]:
        """Get the plan ids based on the environment"""
        env_plans = self.data["env_plan_ids"]
        return env_plans.get(env.environment, [])


def precedence_policy_factory(
    cond_type: str, cond_data: dict[str, Any], binding_policy: BindingPolicy
) -> "BindingPrecedencePolicy":
    """Create a precedence policy object"""
    match cond_type:
        case PrecedencePolicyCondType.REGION_IN.value:
            return RegionInPrecedencePolicy(cond_data=cond_data, binding_policy=binding_policy)
        case PrecedencePolicyCondType.CLUSTER_IN.value:
            return ClusterInPrecedencePolicy(cond_data=cond_data, binding_policy=binding_policy)
        case _:
            raise ValueError(f"Invalid condition type: {cond_type}")


class BindingPrecedencePolicy(abc.ABC):
    """The precedence policy type."""

    binding_policy: BindingPolicy

    def get_plan_ids(self, env: ModuleEnvironment) -> list[str]:
        """Get the plan ids based on the environment"""
        return self.binding_policy.get_plan_ids(env)

    @abc.abstractmethod
    def match(self, env: ModuleEnvironment) -> bool:
        """Check if current precedence policy matches the environment"""
        raise NotImplementedError


@define
class RegionInPrecedencePolicy(BindingPrecedencePolicy):
    """The precedence policy that checks the region is in a list."""

    cond_data: dict[str, Any]
    binding_policy: BindingPolicy

    def match(self, env: ModuleEnvironment) -> bool:
        return env.application.region in self.cond_data["regions"]


@define
class ClusterInPrecedencePolicy(BindingPrecedencePolicy):
    """The precedence policy that checks the cluster name is in a list."""

    cond_data: dict[str, Any]
    binding_policy: BindingPolicy

    def match(self, env: ModuleEnvironment) -> bool:
        cluster_name = EnvClusterService(env).get_cluster_name()
        return cluster_name in self.cond_data["cluster_names"]


def get_service_type(service: ServiceObj) -> str:
    return get_db_properties(service).col_service_type
