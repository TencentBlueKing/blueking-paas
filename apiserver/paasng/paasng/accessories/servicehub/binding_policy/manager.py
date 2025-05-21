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
from typing import Any, Optional

from django.db import transaction
from django.db.models import QuerySet

from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    RuleBasedAllocationPolicy,
    UnifiedAllocationPolicy,
)
from paasng.accessories.servicehub.binding_policy.selector import PlanSelector
from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceAllocationPolicyType,
    ServiceBindingPolicyType,
)
from paasng.accessories.servicehub.models import (
    ServiceAllocationPolicy,
    ServiceBindingPolicy,
    ServiceBindingPrecedencePolicy,
)
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
        self.allocation_policy = ServiceAllocationPolicy.objects.get(
            service_id=self.service.uuid, tenant_id=self.tenant_id
        )

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
            allocation_policy=self.allocation_policy,
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
            allocation_policy=self.allocation_policy,
            tenant_id=self.tenant_id,
            defaults={"type": ServiceBindingPolicyType.ENV_SPECIFIC.value, "data": data},
        )

    def clean_static_policies(self):
        """clean static policies"""
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
        ServiceBindingPrecedencePolicy.objects.create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            allocation_policy=self.allocation_policy,
            tenant_id=self.tenant_id,
            priority=priority,
            cond_type=cond_type.value,
            cond_data=cond_data,
            type=ServiceBindingPolicyType.STATIC.value,
            data=data,
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
        ServiceBindingPrecedencePolicy.objects.create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            allocation_policy=self.allocation_policy,
            tenant_id=self.tenant_id,
            priority=priority,
            cond_type=cond_type.value,
            cond_data=cond_data,
            type=ServiceBindingPolicyType.ENV_SPECIFIC.value,
            data=data,
        )

    def clean_precedence_policies(self):
        """clean the precedence policies"""
        ServiceBindingPrecedencePolicy.objects.filter(service_id=self.service.uuid).delete()

    def get_service_binding_policy(self) -> Optional[ServiceBindingPolicy]:
        try:
            return ServiceBindingPolicy.objects.get(service_id=self.service.uuid, tenant_id=self.tenant_id)
        except ServiceBindingPolicy.DoesNotExist:
            return None

    def get_precedence_policies(self) -> QuerySet[ServiceBindingPrecedencePolicy]:
        return ServiceBindingPrecedencePolicy.objects.filter(
            service_id=self.service.uuid, tenant_id=self.tenant_id
        ).order_by("-priority")


class PolicyCombinationManager:
    """The manager class for policy combination

    :param service: The service object for which the policies are managed.
    :param tenant_id : The unique identifier for the tenant.
    """

    def __init__(self, service: ServiceObj, tenant_id: str):
        self.service = service
        self.tenant_id = tenant_id
        self.service_binding_policy_mgr = ServiceBindingPolicyManager(service, tenant_id)

    def clean(self):
        """Remove policy combination"""
        self.service_binding_policy_mgr.clean_static_policies()
        self.service_binding_policy_mgr.clean_precedence_policies()
        ServiceAllocationPolicy.objects.filter(
            service_id=self.service.uuid,
            tenant_id=self.tenant_id,
        ).delete()

    @transaction.atomic()
    def upsert(self, cfg: PolicyCombinationConfig):
        """Update or insert a combination of service binding policies."""
        self.clean()

        ServiceAllocationPolicy.objects.create(
            service_id=self.service.uuid, tenant_id=self.tenant_id, type=cfg.policy_type
        )

        if cfg.policy_type == ServiceAllocationPolicyType.RULE_BASED.value:
            # 按规则分配
            allocation_precedence_policies = cfg.allocation_precedence_policies
            if not allocation_precedence_policies:
                return
            for config in allocation_precedence_policies:
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

        elif cfg.policy_type == ServiceAllocationPolicyType.UNIFORM.value:
            # 统一分配
            allocation_policy = cfg.allocation_policy
            if not allocation_policy:
                return
            if allocation_policy.plans:
                self.service_binding_policy_mgr.set_static(plans=self._plan_ids_to_objs(allocation_policy.plans))
            elif allocation_policy.env_plans:
                self.service_binding_policy_mgr.set_env_specific(
                    env_plans=self._plan_ids_to_env_plan_objs(allocation_policy.env_plans)
                )

    def get(self) -> Optional[PolicyCombinationConfig]:
        svc_allocation_policy = ServiceAllocationPolicy.objects.get(
            service_id=self.service.uuid,
            tenant_id=self.tenant_id,
        )
        if svc_allocation_policy.type == ServiceAllocationPolicyType.RULE_BASED.value:
            precedence_policies = svc_allocation_policy.rule_based_policies.order_by("-priority")
            allocation_precedence_policies = [
                RuleBasedAllocationPolicy.create_from_policy(policy) for policy in precedence_policies
            ]
            return PolicyCombinationConfig(
                tenant_id=self.tenant_id,
                service_id=self.service.uuid,
                policy_type=svc_allocation_policy.type,
                allocation_precedence_policies=allocation_precedence_policies,
                allocation_policy=None,
            )
        elif svc_allocation_policy.type == ServiceAllocationPolicyType.UNIFORM.value:
            uniform_policy = UnifiedAllocationPolicy.create_from_policy(svc_allocation_policy.uniform_policy)
            return PolicyCombinationConfig(
                tenant_id=self.tenant_id,
                service_id=self.service.uuid,
                policy_type=svc_allocation_policy.type,
                allocation_precedence_policies=None,
                allocation_policy=uniform_policy,
            )

        return None

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


def list_policy_combination_configs(service: ServiceObj) -> list[PolicyCombinationConfig]:
    """
    Retrieve all service policy combination configs
    """

    tenant_ids = ServiceAllocationPolicy.objects.values_list("tenant_id", flat=True)

    result = []
    for tenant_id in tenant_ids:
        mgr = PolicyCombinationManager(service, tenant_id)
        policy_combination = mgr.get()
        if policy_combination is not None:
            result.append(policy_combination)
    return result
