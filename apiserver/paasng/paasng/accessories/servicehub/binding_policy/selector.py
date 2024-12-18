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
from typing import List

from paasng.accessories.servicehub.exceptions import MultiplePlanFoundError, NoPlanFoundError
from paasng.accessories.servicehub.manager import mixed_plan_mgr
from paasng.accessories.servicehub.models import ServiceBindingPolicy, ServiceBindingPrecedencePolicy
from paasng.accessories.servicehub.services import PlanObj, ServiceObj
from paasng.platform.applications.models import ModuleEnvironment

from .policy import binding_policy_factory, precedence_policy_factory


class PlanSelector:
    """The selector that helps to select the plans based on the configured policies"""

    def select(self, service: ServiceObj, env: ModuleEnvironment) -> PlanObj:
        """Select the plan for the env object, might raise an exception if no plan is found
        or multiple plans are found.
        """
        plans = self.list(service, env)
        if len(plans) == 0:
            raise NoPlanFoundError("No plans found")
        elif len(plans) > 1:
            raise MultiplePlanFoundError("Multiple plans found")
        return plans[0]

    def list(self, service: ServiceObj, env: ModuleEnvironment) -> List[PlanObj]:
        """List the plans based on the service and the application"""
        precedence_plans = self._list_precedence(service, env)
        if precedence_plans is not None:
            return precedence_plans

        # Get plans based on the binding policy
        try:
            policy = ServiceBindingPolicy.objects.get(service_id=service.uuid)
        except ServiceBindingPolicy.DoesNotExist:
            return []

        policy_obj = binding_policy_factory(policy.type, policy.data)
        return self.plan_ids_to_objs(service, policy_obj.get_plan_ids(env))

    def _list_precedence(self, service: ServiceObj, env: ModuleEnvironment) -> List[PlanObj] | None:
        """List the plans based on the precedence policies.

        :return: A list plans based on the precedence policies. `None` means no precedence
            policies are evaluated.
        """
        precedence_policies = ServiceBindingPrecedencePolicy.objects.filter(service_id=service.uuid).order_by(
            "-priority"
        )
        for pre_policy in precedence_policies:
            binding_policy = binding_policy_factory(pre_policy.type, pre_policy.data)
            policy_obj = precedence_policy_factory(pre_policy.cond_type, pre_policy.cond_data, binding_policy)
            # If the policy does not match the env object, try the next one
            if not policy_obj.match(env):
                continue
            return self.plan_ids_to_objs(service, policy_obj.get_plan_ids(env))
        return None

    @staticmethod
    def plan_ids_to_objs(service: ServiceObj, plan_ids: List[str]) -> List[PlanObj]:
        """Convert the plan ids to plan objects"""
        all_plans = mixed_plan_mgr.list(service)
        return [p for p in all_plans if p.uuid in plan_ids]
