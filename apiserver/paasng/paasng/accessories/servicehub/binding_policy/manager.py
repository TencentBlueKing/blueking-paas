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
from typing import Any

from django.db import transaction

from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    RuleBasedAllocationConfig,
    UnifiedAllocationConfig,
)
from paasng.accessories.servicehub.binding_policy.selector import PlanSelector
from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceBindingPolicyType,
)
from paasng.accessories.servicehub.models import ServiceBindingPolicy, ServiceBindingPrecedencePolicy
from paasng.accessories.servicehub.services import PlanObj, ServiceObj

from .policy import get_service_type


class ServiceBindingPolicyManager:
    """The manager class for service binding policy

    :param service: The service object for which the policies are managed.
    :param tenant_id : The unique identifier for the tenant.
    """

    def __init__(self, service: ServiceObj, tenant_id: str):
        self.service = service
        self.tenant_id = tenant_id

    def set_static(self, plans: list[PlanObj]):
        """Set the fixed binding policy for the service.

        :param plans: The list of plans to be set as the binding policy.
        """
        if not plans:
            raise ValueError("plans cannot be empty")

        data = {"plan_ids": [p.uuid for p in plans]}
        ServiceBindingPolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            defaults={"type": ServiceBindingPolicyType.STATIC.value, "data": data},
        )

    def set_env_specific(self, env_plans: list[tuple[str, list[PlanObj]]]):
        """Set the environment specific binding policy for the service.

        :param env_plans: A list of tuples, where each tuple contains the environment
            name and the list of plans.
        """
        if not all(plans for _, plans in env_plans):
            raise ValueError("plans cannot be empty")

        data = {"env_plan_ids": {env: [p.uuid for p in plans] for env, plans in env_plans}}
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
        cond_data: dict[str, Any],
        plans: list[PlanObj],
        priority: int = 0,
    ):
        """Add a precedence policy with static binding policy

        :param cond_type: The type of the condition.
        :param cond_data: The data for the condition.
        :param plans: The list of plans to be set as the binding policy.
        :param priority: The priority of the precedence policy.
        """
        if not plans:
            raise ValueError("plans cannot be empty")

        data = {"plan_ids": [p.uuid for p in plans]}
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
        cond_data: dict[str, Any],
        env_plans: list[tuple[str, list[PlanObj]]],
        priority: int = 0,
    ):
        """Add a precedence policy with env specific binding policy

        :param cond_type: The type of the condition.
        :param cond_data: The data for the condition.
        :param env_plans: A list of tuples, where each tuple contains the environment
            name and the list of plans.
        :param priority: The priority of the precedence policy.
        """
        if not all(plans for _, plans in env_plans):
            raise ValueError("plans cannot be empty")

        data = {"env_plan_ids": {env: [p.uuid for p in plans] for env, plans in env_plans}}
        ServiceBindingPrecedencePolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            priority=priority,
            defaults={
                "cond_type": cond_type.value,
                "cond_data": cond_data,
                "type": ServiceBindingPolicyType.ENV_SPECIFIC.value,
                "data": data,
                "priority": priority,
            },
        )

    def remove_all_precedence_policies(self, priority: int | None = None):
        """Remove all the precedence policies"""
        qs = ServiceBindingPrecedencePolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id)
        if priority is not None:
            qs = qs.filter(priority=priority)
        qs.delete()


class PolicyCombinationManager:
    """The manager class for policy combination

    :param service: The service object for which the policies are managed.
    :param tenant_id : The unique identifier for the tenant.
    """

    def __init__(self, service: ServiceObj, tenant_id: str):
        self.service = service
        self.tenant_id = tenant_id
        self.service_binding_policy_mgr = ServiceBindingPolicyManager(service, tenant_id)

    def remove_policy_combination(self):
        """Remove policy combination"""
        self.service_binding_policy_mgr.clean_static_policies()
        self.service_binding_policy_mgr.remove_all_precedence_policies()

    @transaction.atomic()
    def upsert_policy_combination(self, policy_combination_config: PolicyCombinationConfig):
        """Update or insert a combination of service binding policies."""
        self.remove_policy_combination()

        rule_based_allocation_configs = policy_combination_config.rule_based_allocation_configs
        unified_allocation_config = policy_combination_config.unified_allocation_config

        # Set the base policy
        if unified_allocation_config.plans:
            self.service_binding_policy_mgr.set_static(plans=self._plan_ids_to_objs(unified_allocation_config.plans))
        elif unified_allocation_config.env_plans:
            self.service_binding_policy_mgr.set_env_specific(
                env_plans=self._plan_ids_to_env_plan_objs(unified_allocation_config.env_plans)
            )

        # Add precedence policies with decreasing priority
        for config in rule_based_allocation_configs:
            if config.plans:
                self.service_binding_policy_mgr.add_precedence_static(
                    cond_type=PrecedencePolicyCondType(config.cond_type),
                    cond_data=config.cond_data,
                    plans=self._plan_ids_to_objs(config.plans),
                    priority=config.priority,
                )
            elif config.env_plans:
                self.service_binding_policy_mgr.add_precedence_env_specific(
                    cond_type=PrecedencePolicyCondType(config.cond_type),
                    cond_data=config.cond_data,
                    env_plans=self._plan_ids_to_env_plan_objs(config.env_plans),
                    priority=config.priority,
                )

    def get_tenant_policy_combination_config(self) -> PolicyCombinationConfig:
        precedence_policies = ServiceBindingPrecedencePolicy.objects.filter(tenant_id=self.tenant_id).order_by(
            "-priority"
        )
        service_binding_policy = ServiceBindingPolicy.objects.get(
            service_id=self.service.uuid, tenant_id=self.tenant_id
        )
        rule_based_configs = [RuleBasedAllocationConfig.create_from_policy(policy) for policy in precedence_policies]
        unified_config = UnifiedAllocationConfig.create_from_policy(service_binding_policy)
        return PolicyCombinationConfig(
            tenant_id=self.tenant_id,
            service_id=self.service.uuid,
            rule_based_allocation_configs=rule_based_configs,
            unified_allocation_config=unified_config,
        )

    def _plan_ids_to_objs(self, plan_ids: list[str]) -> list[PlanObj]:
        selector = PlanSelector()
        plan_objs = selector.plan_ids_to_objs(self.service, plan_ids)
        return plan_objs

    def _plan_ids_to_env_plan_objs(self, env_plan_ids: dict[str, list[str]]) -> list[tuple[str, list[PlanObj]]]:
        selector = PlanSelector()
        env_plan_objs: list[tuple[str, list[PlanObj]]] = [
            (env, selector.plan_ids_to_objs(self.service, plan_ids)) for env, plan_ids in env_plan_ids.items()
        ]
        return env_plan_objs


def get_all_policy_combination_configs(service: ServiceObj) -> list[PolicyCombinationConfig]:
    """
    Retrieve all service policy combination configs
    """

    # Retrieve all policies and order them by tenant_id and priority (descending)
    tenant_ids = set(ServiceBindingPrecedencePolicy.objects.values_list("tenant_id", flat=True)).union(
        set(ServiceBindingPolicy.objects.values_list("tenant_id", flat=True))
    )

    result = []
    for tenant_id in tenant_ids:
        mgr = PolicyCombinationManager(service, tenant_id)
        result.append(mgr.get_tenant_policy_combination_config())
    return result
