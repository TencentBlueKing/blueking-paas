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

from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceBindingPolicyType,
)
from paasng.accessories.servicehub.models import ServiceBindingPolicy, ServiceBindingPrecedencePolicy
from paasng.accessories.servicehub.services import PlanObj, ServiceObj

from .policy import get_service_type


class ServiceBindingPolicyManager:
    """The manager class for service binding policy"""

    def __init__(self, service: ServiceObj):
        self.service = service

    def set_static(self, plans: list[PlanObj]):
        """Set the fixed binding policy for the service.

        :param plans: The list of plans to be set as the binding policy.
        """
        if not plans:
            raise ValueError("plans cannot be empty")

        data = {"plans": [p.uuid for p in plans]}
        ServiceBindingPolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            defaults={"type": ServiceBindingPolicyType.STATIC.value, "data": data},
        )

    def set_env_specific(self, env_plans: list[tuple[str, list[PlanObj]]]):
        """Set the environment specific binding policy for the service.

        :param env_plans: A list of tuples, where each tuple contains the environment
            name and the list of plans.
        """
        if not all(plans for _, plans in env_plans):
            raise ValueError("plans cannot be empty")

        data = {"env_plans": {env: [p.uuid for p in plans] for env, plans in env_plans}}
        ServiceBindingPolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            defaults={"type": ServiceBindingPolicyType.ENV_SPECIFIC.value, "data": data},
        )

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

        data = {"plans": [p.uuid for p in plans]}
        ServiceBindingPrecedencePolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            defaults={
                "cond_type": cond_type.value,
                "cond_data": cond_data,
                "type": ServiceBindingPolicyType.STATIC.value,
                "data": data,
                "priority": priority,
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

        data = {"env_plans": {env: [p.uuid for p in plans] for env, plans in env_plans}}
        ServiceBindingPrecedencePolicy.objects.update_or_create(
            service_id=self.service.uuid,
            service_type=get_service_type(self.service),
            defaults={
                "cond_type": cond_type.value,
                "cond_data": cond_data,
                "type": ServiceBindingPolicyType.ENV_SPECIFIC.value,
                "data": data,
                "priority": priority,
            },
        )

    def clean_precedence_policies(self):
        """Remove all the precedence policies"""
        ServiceBindingPrecedencePolicy.objects.filter(service_id=self.service.uuid).delete()
