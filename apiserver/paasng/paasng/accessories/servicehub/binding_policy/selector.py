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
import logging
from enum import StrEnum
from typing import Dict, List

from paasng.accessories.servicehub.constants import ServiceAllocationPolicyType
from paasng.accessories.servicehub.exceptions import MultiplePlanFoundError, NoPlanFoundError, PlanSelectorError
from paasng.accessories.servicehub.models import (
    ServiceAllocationPolicy,
    ServiceBindingPolicy,
    ServiceBindingPrecedencePolicy,
)
from paasng.accessories.servicehub.services import PlanObj, ServiceObj
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models.module import Module

from .policy import binding_policy_factory, precedence_policy_factory

logger = logging.getLogger(__name__)


def get_plan_by_env(
    service: ServiceObj, env: ModuleEnvironment, plan_id: str | None, env_plan_id_map: dict[str, str] | None
) -> PlanObj:
    """Return the plan that matching the given conditions.

    The plan_id and env_plan_id_map are optional, if both are not provided, the plan
    selector will be used to select a plan.

    :param env: The module env obj.
    :param plan_id: Optional, The plan id
    :param env_plan_id_map: Optional, The plan id map, structure: {env_name: plan_id, ...}.
    :return: A Plan object.
    :raise ValueError: When unable to find a plan by given parameters.
    """
    selector = PlanSelector()

    if plan_id:
        key = plan_id
    elif env_plan_id_map:
        key = env_plan_id_map[env.environment]
    else:
        try:
            return selector.select(service, env)
        except PlanSelectorError as e:
            raise ValueError(f"Unable to select a plan: {e}")

    plans = selector.list(service, env)
    # Try to find the plan object by the given plan id
    if not plans:
        raise ValueError("no plans found")
    plan = next((p for p in plans if p.uuid == key), None)
    if not plan:
        raise ValueError("no plan found by given plan_id")
    return plan


class PlanSelector:
    """The selector that helps to select the plans based on the configured policies"""

    def list_possible_plans(self, service: ServiceObj, module: Module) -> "PossiblePlans":
        """List the possible plans for the service and the module. Can be one of these
        situations:

        - static with a single plan
        - static with multiple plans
        - env specific, each env has different plans(can be single or multiple)
        """
        data: Dict[str, List[PlanObj]] = {}
        for env in module.envs.all():
            data[env.environment] = self.list(service, env)
        return PossiblePlans(env_plans=data)

    def select(self, service: ServiceObj, env: ModuleEnvironment) -> PlanObj:
        """Select the plan for the env object, might raise an exception if no plan is found
        or multiple plans are found.

        :raise NoPlanFoundError: If no plan is found
        :raise MultiplePlanFoundError: If multiple plans are found
        """
        plans = self.list(service, env)
        if len(plans) == 0:
            raise NoPlanFoundError("no plans found")
        elif len(plans) > 1:
            raise MultiplePlanFoundError("multiple plans found")
        return plans[0]

    def list(self, service: ServiceObj, env: ModuleEnvironment) -> List[PlanObj]:
        """List the plans based on the service and the application"""
        alloc_type = ServiceAllocationPolicy.objects.get_type(service, env.tenant_id)
        if alloc_type == ServiceAllocationPolicyType.RULE_BASED.value:
            return self._list_rule_based_policies(service, env)
        elif alloc_type == ServiceAllocationPolicyType.UNIFORM.value:
            return self._get_uniform_policy(service, env)

        raise ValueError("Unsupported ServiceAllocationPolicy type: %s" % alloc_type)

    def _get_uniform_policy(self, service: ServiceObj, env: ModuleEnvironment) -> List[PlanObj]:
        """get the plans based on the ServiceBindingPolicy.

        :return: A list plans based on the ServiceBindingPolicy.
        """
        # Get plans based on the binding policy
        try:
            policy = ServiceBindingPolicy.objects.get(service_id=service.uuid, tenant_id=env.tenant_id)
        except ServiceBindingPolicy.DoesNotExist:
            return []

        policy_obj = binding_policy_factory(policy.type, policy.data)
        return self.plan_ids_to_objs(service, policy_obj.get_plan_ids(env))

    def _list_rule_based_policies(self, service: ServiceObj, env: ModuleEnvironment) -> List[PlanObj]:
        """List the plans based on the ServiceBindingPrecedencePolicy.

        :return: A list plans based on the ServiceBindingPrecedencePolicy.
        :raise ValueError: If no precedence policy matches the env object.
        """
        precedence_policies = ServiceBindingPrecedencePolicy.objects.filter(
            service_id=service.uuid, tenant_id=env.tenant_id
        ).order_by("-priority")
        for pre_policy in precedence_policies:
            policy_obj = precedence_policy_factory(
                pre_policy.cond_type,
                pre_policy.cond_data,
                binding_policy=binding_policy_factory(pre_policy.type, pre_policy.data),
            )
            # If the policy does not match the env object, try the next one
            if not policy_obj.match(env):
                continue
            return self.plan_ids_to_objs(service, policy_obj.get_plan_ids(env))
        raise ValueError("Can not match any plans")

    @staticmethod
    def plan_ids_to_objs(service: ServiceObj, plan_ids: List[str]) -> List[PlanObj]:
        """Convert the plan ids to plan objects"""
        index = {p.uuid: p for p in service.get_plans()}
        return [index[plan_id] for plan_id in plan_ids]


class PossiblePlansResultType(StrEnum):
    """The type of possible plans result.

    It may look like `ServiceBindingPolicyType` but it is not the same. `PossiblePlansResultType`
    is the "final" result of many policies. For example, if a service has been configured
    to use the same plans for different envs, then the policy type might be `ENV_SPECIFIC`
    but the `PossiblePlansResultType` is `STATIC`.
    """

    STATIC = "static"
    ENV_SPECIFIC = "env_specific"


class PossiblePlans:
    """The possible plans for the service and the module. This object helps the client
    to know the plans and use a proper way to interact with them.

    :param env_plans: The plans for each environment.
    """

    def __init__(self, env_plans: Dict[str, List[PlanObj]]):
        self._has_multiple_plans = False
        self._result_type = PossiblePlansResultType.STATIC

        self.env_plans = env_plans
        self._parse(self.env_plans)

    def has_multiple_plans(self) -> bool:
        """Whether there are multiple plans available. If this is True, then the
        client should choose the plan manually.
        """
        return self._has_multiple_plans

    def get_result_type(self) -> PossiblePlansResultType:
        """Return the result type of the possible plans."""
        return self._result_type

    def get_static_plans(self) -> List[PlanObj] | None:
        """Get the static plans.

        :return: The plan list, None if current object is not static.
        """
        if self.get_result_type() != PossiblePlansResultType.STATIC:
            return None
        return next(iter(self.env_plans.values()), None)

    def get_env_specific_plans(self) -> Dict[str, List[PlanObj]] | None:
        """Get the env specific plans.

        :return: The plans dict, None if current object is not env specific.
        """
        if self.get_result_type() != PossiblePlansResultType.ENV_SPECIFIC:
            return None
        return self.env_plans

    def _parse(self, env_plans: Dict[str, List[PlanObj]]):
        """Parse the env plans to set the attributes."""
        # If no plans are found, return directly to leave the properties as False
        if not any(plans for plans in env_plans.values()):
            return

        self._has_multiple_plans = any(len(plans) > 1 for plans in self.env_plans.values())

        last_sorted_ids = None
        # If any plans are different with others, then it is not static
        for plans in self.env_plans.values():
            sorted_ids = tuple(sorted(str(p.uuid) for p in plans))
            if last_sorted_ids is not None and last_sorted_ids != sorted_ids:
                self._result_type = PossiblePlansResultType.ENV_SPECIFIC
                return
            last_sorted_ids = sorted_ids
