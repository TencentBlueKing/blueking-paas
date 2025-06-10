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
from typing import Any, List

from django.db import transaction

from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    ServiceBindingPolicyDTO,
    ServiceBindingPrecedencePolicyDTO,
)
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
from paasng.accessories.servicehub.services import ServiceObj

from .policy import get_service_type


class SvcBindingPolicyManager:
    """The manager class for service binding policy.

    :param service: The service object for which the policies are managed.
    :param tenant_id : The unique identifier for the tenant.
    """

    def __init__(self, service: ServiceObj, tenant_id: str):
        self.service = service
        self.tenant_id = tenant_id

    def get_comb_cfg(self) -> PolicyCombinationConfig | None:
        """Get the configured policies as a PolicyCombinationConfig object.

        *A combination config is a data structure containing service policies. it's
        specifically used by the frontend client.*

        :return: None if no configurations can be found.
        """
        pre_policies = self._get_precedence_policies()
        policy = self._get_service_binding_policy()
        if pre_policies is None and policy is None:
            return None

        alloc_type = ServiceAllocationPolicy.objects.get_type(self.service, self.tenant_id)
        cfg = PolicyCombinationConfig(
            tenant_id=self.tenant_id,
            service_id=self.service.uuid,
            policy_type=alloc_type.value,
            allocation_precedence_policies=pre_policies,
            allocation_policy=policy,
        )

        # TODO: 暂时和集群分配一致，仅保留当前类型的数据，后续修改为无论什么分配类型下都保存/渲染两种类型的数据
        match alloc_type:
            case ServiceAllocationPolicyType.RULE_BASED:
                cfg.allocation_policy = None
            case ServiceAllocationPolicyType.UNIFORM:
                cfg.allocation_precedence_policies = None
        return cfg

    @transaction.atomic()
    def save_comb_cfg(self, cfg: PolicyCombinationConfig):
        """Save a combination config object.

        *A combination config is a data structure containing service policies. it's
        specifically used by the frontend client.*

        :raises ValueError: If the given config is invalid.
        """
        if cfg.policy_type == ServiceAllocationPolicyType.RULE_BASED.value:
            policies = cfg.allocation_precedence_policies
            if not policies:
                raise ValueError(
                    "Allocation precedence policies cannot be None or empty when policy_type is rule_based."
                )
            self.set_rule_based(policies)
        elif cfg.policy_type == ServiceAllocationPolicyType.UNIFORM.value:
            policy = cfg.allocation_policy
            if not policy:
                raise ValueError("Allocation policy cannot be None when policy_type is uniform.")
            self.set_uniform(policy.plans, policy.env_plans)

    def set_uniform(
        self,
        plans: list[str] | None = None,
        env_plans: dict[str, list[str]] | None = None,
    ):
        """Set the binding policy for the service, it also set the policy type to UNIFORM.

        :param plans: The list of plan IDs.
        :param env_plans: A dict of env name and a list of plan IDs.
        :raises ValueError: When the given plans are invalid.
        """
        type_, data = self._to_policy_type_data(plans, env_plans)
        ServiceAllocationPolicy.objects.set_type_uniform(self.service, self.tenant_id)
        ServiceBindingPolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            tenant_id=self.tenant_id,
            defaults={"type": type_, "data": data},
        )

    def set_rule_based(self, policies: list[ServiceBindingPrecedencePolicyDTO]):
        """Set the binding policies for the service, it also set the policy type to RULE_BASED.

        :param policies: A list of precedence policies.
        """
        # Validate: 检查最低优先级的策略是否为 always_match
        min_priority_policy = min(policies, key=lambda p: p.priority)
        if min_priority_policy.cond_type != PrecedencePolicyCondType.ALWAYS_MATCH.value:
            raise ValueError("The policy with the minimum priority must be 'always_match'.")

        ServiceAllocationPolicy.objects.set_type_rule_based(self.service, self.tenant_id)
        ServiceBindingPrecedencePolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id).delete()
        for config in policies:
            type_, data = self._to_policy_type_data(config.plans, config.env_plans)
            cond_type = PrecedencePolicyCondType(config.cond_type)
            ServiceBindingPrecedencePolicy.objects.create(
                service_id=self.service.uuid,
                service_type=get_service_type(self.service),
                tenant_id=self.tenant_id,
                priority=config.priority,
                cond_type=cond_type.value,
                cond_data=config.cond_data,
                type=type_,
                data=data,
            )

    def clean(self):
        """Remove all configurations."""
        ServiceAllocationPolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id).delete()
        ServiceBindingPolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id).delete()
        ServiceBindingPrecedencePolicy.objects.filter(service_id=self.service.uuid, tenant_id=self.tenant_id).delete()

    def _get_precedence_policies(self) -> List[ServiceBindingPrecedencePolicyDTO] | None:
        """Get all precedence policies for the service."""
        qs = ServiceBindingPrecedencePolicy.objects.filter(
            service_id=self.service.uuid, tenant_id=self.tenant_id
        ).order_by("-priority")
        if not qs:
            return None
        return [ServiceBindingPrecedencePolicyDTO.from_db_obj(policy) for policy in qs]

    def _get_service_binding_policy(self) -> ServiceBindingPolicyDTO | None:
        """Get the service binding policy for the service."""
        try:
            obj = ServiceBindingPolicy.objects.get(service_id=self.service.uuid, tenant_id=self.tenant_id)
            return ServiceBindingPolicyDTO.from_db_obj(obj)
        except ServiceBindingPolicy.DoesNotExist:
            return None

    def _to_policy_type_data(
        self, plans: list[str] | None, env_plans: dict[str, list[str]] | None
    ) -> tuple[str, dict[str, Any]]:
        """Convert the given plans and env_plans to a policy type and data dict for saving.

        :return: (policy_type, policy_data)
        """
        if plans and env_plans:
            raise ValueError("Cannot set both plans and env_plans at the same time.")
        elif not plans and not env_plans:
            raise ValueError("Must provide either plans or env_plans.")

        data: dict[str, Any]
        if plans:
            self._validate_plans(plans)
            data = {"plan_ids": plans}
            return ServiceBindingPolicyType.STATIC.value, data
        elif env_plans:
            self._validate_env_plans(env_plans)
            data = {"env_plan_ids": env_plans}
            return ServiceBindingPolicyType.ENV_SPECIFIC.value, data
        raise ValueError("Must provide either plans or env_plans.")

    def _validate_plans(self, plans: list[str] | None):
        """Validate the given plan ids to check if them belongs to the current service."""
        index = {p.uuid for p in self.service.get_plans()}
        for plan_id in plans or []:
            if plan_id not in index:
                raise ValueError(f"Plan {plan_id} does not belong to service {self.service.uuid}.")

    def _validate_env_plans(self, env_plans: dict[str, list[str]] | None):
        """Validate the given environment plan ids to check if they belong to the current service."""
        if not env_plans:
            return
        if not all(env_plans.values()):
            raise ValueError("plans cannot be empty")
        index = {p.uuid for p in self.service.get_plans()}
        for plans in env_plans.values():
            for plan_id in plans:
                if plan_id not in index:
                    raise ValueError(f"Plan {plan_id} does not belong to service {self.service.uuid}.")


def list_policy_combination_configs(service: ServiceObj) -> list[PolicyCombinationConfig]:
    """Retrieve all service policy combination configs"""
    tenant_ids = ServiceAllocationPolicy.objects.values_list("tenant_id", flat=True).distinct()

    result = []
    for tenant_id in tenant_ids:
        mgr = SvcBindingPolicyManager(service, tenant_id)
        policy_combination = mgr.get_comb_cfg()
        if policy_combination is not None:
            result.append(policy_combination)
    return result
