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
from collections import defaultdict
from typing import Any

from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    RuleBasedAllocationConfig,
    UnifiedAllocationConfig,
)
from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceBindingPolicyType,
)
from paasng.accessories.servicehub.models import ServiceBindingPolicy, ServiceBindingPrecedencePolicy
from paasng.accessories.servicehub.services import ServiceObj
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID

from .policy import get_service_type


class ServiceBindingPolicyManager:
    """The manager class for service binding policy"""

    def __init__(self, service: ServiceObj, tenant_id: str = DEFAULT_TENANT_ID):
        self.service = service
        self.tenant_id = tenant_id

    def set_static(self, plans: list[str]):
        """Set the fixed binding policy for the service.

        :param plans: The list of plan uuids to be set as the binding policy.
        """
        if not plans:
            raise ValueError("plans cannot be empty")

        data = {"plan_ids": plans}
        ServiceBindingPolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            defaults={"type": ServiceBindingPolicyType.STATIC.value, "data": data},
        )

    def set_env_specific(self, env_plans: dict[str, list[str]]):
        """Set the environment specific binding policy for the service.

        :param env_plans: A list of tuples, where each tuple contains the environment
            name and the list of plan uuids.
        """
        if not all(plans for _, plans in env_plans.items()):
            raise ValueError("plans cannot be empty")

        data = {"env_plan_ids": env_plans}
        ServiceBindingPolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            defaults={"type": ServiceBindingPolicyType.ENV_SPECIFIC.value, "data": data},
        )

    def clean_static_policies(self):
        """Remove all the static policies"""
        ServiceBindingPolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id).delete()

    def add_precedence_static(
        self,
        cond_type: PrecedencePolicyCondType,
        # TODO: cond_data 应该输入纯粹的 plans 而不是在函数内在另外的函数内限制格式
        cond_data: dict[str, Any],
        plans: list[str],
        priority: int = 0,
    ):
        """Add a precedence policy with static binding policy

        :param cond_type: The type of the condition.
        :param cond_data: The data for the condition.
        :param plans: The list of plan uuids to be set as the binding policy.
        :param priority: The priority of the precedence policy.
        """
        if not plans:
            raise ValueError("plans cannot be empty")

        data = {"plan_ids": plans}
        ServiceBindingPrecedencePolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            priority=priority,
            defaults={
                "cond_type": cond_type.value,
                "cond_data": cond_data,
                "type": ServiceBindingPolicyType.STATIC.value,
                "data": data,
            },
        )

    def add_precedence_env_specific(
        self,
        cond_type: PrecedencePolicyCondType,
        # TODO: cond_data 应该输入纯粹的 plans 而不是在函数内在另外的函数内限制格式
        cond_data: dict[str, Any],
        env_plans: dict[str, list[str]],
        priority: int = 0,
    ):
        """Add a precedence policy with env specific binding policy

        :param cond_type: The type of the condition.
        :param cond_data: The data for the condition.
        :param env_plans: A dictionary mapping environment names to lists of plan uuids.
        :param priority: The priority of the precedence policy.
        """
        if not all(plans for _, plans in env_plans.items()):
            raise ValueError("plans cannot be empty")

        ServiceBindingPrecedencePolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            priority=priority,
            defaults={
                "cond_type": cond_type.value,
                "cond_data": cond_data,
                "type": ServiceBindingPolicyType.ENV_SPECIFIC.value,
                "data": {"env_plan_ids": env_plans},
            },
        )

    def clean_precedence_policies(self, priority: int | None = None):
        """Remove all the precedence policies"""
        qs = ServiceBindingPrecedencePolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id)
        if priority is not None:
            qs = qs.filter(priority=priority)
        qs.delete()

    def clean_policy_combination(self):
        """Remove all policies"""
        self.clean_static_policies()
        self.clean_precedence_policies()

    def upsert_policy_combination(self, policy_combination_config: PolicyCombinationConfig):
        """Update or insert a combination of service binding policies."""
        self.clean_policy_combination()
        rule_based_allocation_configs = policy_combination_config.rule_based_allocation_configs
        unified_allocation_config = policy_combination_config.unified_allocation_config

        # Set the base policy
        if unified_allocation_config.plans:
            self.set_static(plans=unified_allocation_config.plans)
        elif unified_allocation_config.env_plans:
            self.set_env_specific(env_plans=unified_allocation_config.env_plans)

        # Add precedence policies with decreasing priority
        for config in rule_based_allocation_configs:
            if config.plans:
                self.add_precedence_static(
                    cond_type=PrecedencePolicyCondType(config.cond_type),
                    cond_data=config.cond_data,
                    plans=config.plans,
                    priority=config.priority,
                )
            elif config.env_plans:
                self.add_precedence_env_specific(
                    cond_type=PrecedencePolicyCondType(config.cond_type),
                    cond_data=config.cond_data,
                    env_plans=config.env_plans,
                    priority=config.priority,
                )

    def get_policy_combination_configs(self) -> list[PolicyCombinationConfig]:
        # Retrieve all policy combination if the tenant is an operation tenant.
        # Otherwise, retrieve the single policy combination.
        if self.tenant_id == OP_TYPE_TENANT_ID:
            return self.get_all_policy_combination_config()
        else:
            return self.get_tenant_policy_combination_config()

    def get_all_policy_combination_config(self) -> list[PolicyCombinationConfig]:
        """
        Retrieve all service binding precedence policies, group them by tenant_id,
        and construct a list of policy combinations for each tenant.
        """

        # Retrieve all policies and order them by tenant_id and priority (descending)
        precedence_policies = ServiceBindingPrecedencePolicy.objects.all().order_by("tenant_id", "-priority")

        # Group policies by tenant_id
        grouped_policies = defaultdict(list)
        for policy in precedence_policies:
            grouped_policies[policy.tenant_id].append(policy)

        result = []
        for tenant_id, policies in grouped_policies.items():
            service_binding_policy = ServiceBindingPolicy.objects.get(
                service_id=self.service.uuid, tenant_id=tenant_id
            )
            rule_based_configs = [RuleBasedAllocationConfig.create_by_policy(policy) for policy in policies]
            unified_config = UnifiedAllocationConfig.create_by_policy(service_binding_policy)
            result.append(
                PolicyCombinationConfig(
                    tenant_id=tenant_id,
                    rule_based_allocation_configs=rule_based_configs,
                    unified_allocation_config=unified_config,
                )
            )
        return result

    def get_tenant_policy_combination_config(self) -> list[PolicyCombinationConfig]:
        precedence_policies = ServiceBindingPrecedencePolicy.objects.filter(tenant_id=self.tenant_id).order_by(
            "-priority"
        )
        service_binding_policy = ServiceBindingPolicy.objects.get(
            service_id=self.service.uuid, tenant_id=self.tenant_id
        )
        rule_based_configs = [RuleBasedAllocationConfig.create_by_policy(policy) for policy in precedence_policies]
        unified_config = UnifiedAllocationConfig.create_by_policy(service_binding_policy)
        return [
            PolicyCombinationConfig(
                tenant_id=self.tenant_id,
                rule_based_allocation_configs=rule_based_configs,
                unified_allocation_config=unified_config,
            )
        ]
