# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from typing import Any, Self

from attrs import define

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceBindingPolicyType,
    ServiceUsage,
)
from paasng.accessories.servicehub.models import ServiceBindingPolicy, ServiceBindingPrecedencePolicy
from paasng.accessories.servicehub.services import ServiceObj
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import SourceOrigin


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


@define
class BindingPrecedencePolicy:
    """基于 matcher dict 的规则分配策略.

    不变量:
    - 空 matcher {} 表示无条件命中的兜底规则，有且仅有一条，且优先级最低
    - 非兜底规则必须显式声明 matcher, 且仅含单个条件 key (当前不支持多条件组合)
    - matcher key 必须属于 PrecedencePolicyCondType 枚举值，非法 key 会在 match() 时抛 ValueError

    :param matcher: 匹配条件, 单 key dict 或空 dict, 例如:
        - {"region_in": ["default", "tencent"]}
        - {"cluster_in": ["devcloud-gz"]}
        - {"usage_in": ["ai_agent"]}
        - {} 空字典表示无条件命中 (兜底规则)

    :param binding_policy: 匹配后使用的 plan 分配策略
    """

    matcher: dict[str, list[str]]
    binding_policy: BindingPolicy

    def get_plan_ids(self, env: ModuleEnvironment) -> list[str]:
        """Get the plan ids based on the environment"""
        return self.binding_policy.get_plan_ids(env)

    def match(self, env: ModuleEnvironment) -> bool:
        if not self.matcher:
            return True

        if len(self.matcher) != 1:
            raise ValueError(f"Expected exactly one matcher condition, got {len(self.matcher)}")

        ((cond_type_str, values),) = self.matcher.items()
        cond_type = PrecedencePolicyCondType(cond_type_str)
        if cond_type == PrecedencePolicyCondType.REGION_IN:
            if env.application.region not in values:
                return False
        elif cond_type == PrecedencePolicyCondType.CLUSTER_IN:
            cluster_name = EnvClusterService(env).get_cluster_name()
            if cluster_name not in values:
                return False
        elif cond_type == PrecedencePolicyCondType.USAGE_IN:
            usage = get_env_usage(env)
            if usage is None or usage not in values:
                return False
        else:
            raise ValueError(f"Unknown condition type: {cond_type_str}")
        return True


def get_env_usage(env: ModuleEnvironment) -> str | None:
    """Get the usage from the module environment."""
    if env.application.is_ai_agent_app:
        return ServiceUsage.AI_AGENT.value
    if env.module_id and env.module.get_source_origin() == SourceOrigin.AI_AGENT:
        return ServiceUsage.AI_AGENT.value
    return None


def get_service_type(service: ServiceObj) -> str:
    # TODO: Fix the circular import issue
    from paasng.accessories.servicehub.manager import get_db_properties

    return get_db_properties(service).col_service_type


@define
class ServiceBindingPolicyDTO:
    """The DTO object for ServiceBindingPolicy."""

    plans: list[str] | None = None
    env_plans: dict[str, list[str]] | None = None

    @classmethod
    def from_db_obj(cls, policy: ServiceBindingPolicy) -> Self:
        return cls(
            plans=policy.data.get("plan_ids", None),
            env_plans=policy.data.get("env_plan_ids", None),
        )


@define
class ServiceBindingPrecedencePolicyDTO:
    """The DTO object for ServiceBindingPrecedencePolicy."""

    matcher: dict[str, list[str]]
    priority: int
    plans: list[str] | None = None
    env_plans: dict[str, list[str]] | None = None

    @classmethod
    def from_db_obj(cls, policy: ServiceBindingPrecedencePolicy) -> Self:
        return cls(
            matcher=policy.matcher,
            priority=policy.priority,
            plans=policy.data.get("plan_ids", None),
            env_plans=policy.data.get("env_plan_ids", None),
        )


@define
class PolicyCombinationConfig:
    """The configuration for building policy combination.

    This class provides two mutually exclusive approaches for service binding allocation:

    1. Rule-based Precedence Policies:
       - Evaluates multiple conditions in priority order
       - First matching condition determines the allocation
       - The policy with the lowest priority should have an empty matcher ({}) as the guaranteed fallback

    2. Unified Allocation Policy:
       - Applies a single allocation rule to all cases
       - Simpler configuration for uniform allocation needs

    Example Usage:
    - If the region is "region_default", assign plans ["plan_region"].
    - Else if the cluster is "cluster_default", assign plans ["plan_cluster"].
    - Fallback to plans ["plan_default"] if none of the above conditions are met.

    This can be represented as:

    ```
    PolicyCombinationConfig(
        tenant_id="tenant_x",
        service_id="service_x",
        policy_type="rule_based",
        allocation_precedence_policies=[
            ServiceBindingPrecedencePolicyDTO(
                matcher={"region_in": ["region_default"]},
                priority=2,
                plans=["plan_region"]
            ),
            ServiceBindingPrecedencePolicyDTO(
                matcher={"cluster_in": ["cluster_default"]},
                priority=1,
                plans=["plan_cluster"]
            ),
            ServiceBindingPrecedencePolicyDTO(
                matcher={},
                priority=0,
                plans=["plan_default"]
            )
        ],
        allocation_policy=None,
    )
    ```

    Example Usage:
    - Allocate the same plans ["plan_unified"] to all service bindings

    Configuration Example:
    ```
    PolicyCombinationConfig(
        tenant_id="tenant_x",
        service_id="service_x",
        policy_type="uniform",
        allocation_precedence_policies=None,
        allocation_policy=ServiceBindingPolicyDTO(
            plans=["plan_unified"],
        )
    )
    ```
    """

    tenant_id: str
    service_id: str
    # 枚举值 -> ServiceAllocationPolicyType
    policy_type: str
    # 按规则分配
    allocation_precedence_policies: list[ServiceBindingPrecedencePolicyDTO] | None = None
    # 统一分配
    allocation_policy: ServiceBindingPolicyDTO | None = None
