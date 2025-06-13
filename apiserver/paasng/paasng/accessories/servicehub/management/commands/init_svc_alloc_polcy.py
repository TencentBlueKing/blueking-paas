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


import logging

from django.core.management.base import BaseCommand
from django.db.models import Min

from paasng.accessories.servicehub.binding_policy.policy import get_service_type
from paasng.accessories.servicehub.constants import (
    PrecedencePolicyCondType,
    ServiceAllocationPolicyType,
    ServiceBindingPolicyType,
)
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import (
    ServiceAllocationPolicy,
    ServiceBindingPolicy,
    ServiceBindingPrecedencePolicy,
)
from paasng.utils.validators import str2bool

logger = logging.getLogger("commands")


class Command(BaseCommand):
    """
    初始化 ServiceAllocationPolicy.

    背景:
    ServiceBindingPrecedencePolicy 本身用于带条件匹配，ServiceBindingPolicy 用于无条件匹配，作为兜底策略。
    本次修改后，ServiceBindingPrecedencePolicy 用于规则匹配，使用类型为 "AlwaysMatch" 作为兜底策略。
    ServiceBindingPolicy 用于统一分配。
    并且添加了模型 ServiceAllocationPolicy 存储和判断分配策略（规则匹配/统一分配）
    目的:
    - 将带条件匹配 ServiceBindingPolicy 兜底策略转换为 always_match ServiceBindingPrecedencePolicy
    - 为带条件匹配创建 rule_based 类型的 ServiceAllocationPolicy
    - 根据孤立的 ServiceBindingPolicy 创建 uniform 类型的 ServiceAllocationPolicy
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", default=True, type=str2bool, help="避免意外触发, 若想执行需添加该参数"
        )

    def handle(self, dry_run: bool, *args, **kwargs):
        processed_pairs = set()
        for precedence_policy in ServiceBindingPrecedencePolicy.objects.all():
            service_id = precedence_policy.service_id
            tenant_id = precedence_policy.tenant_id
            # 若处理过则跳过
            if (service_id, tenant_id) in processed_pairs:
                continue
            processed_pairs.add((service_id, tenant_id))

            service_obj = mixed_service_mgr.get(uuid=service_id)
            policy = ServiceBindingPolicy.objects.get(
                service_id=service_id,
                tenant_id=tenant_id,
            )
            plans = policy.data
            # 获取最小 priority
            min_priority = ServiceBindingPrecedencePolicy.objects.filter(
                service_id=service_id, tenant_id=tenant_id
            ).aggregate(Min("priority"))["priority__min"]
            # 转换为 ServiceBindingPrecedencePolicy，即创建 always_match ServiceBindingPrecedencePolicy
            if policy.type == ServiceBindingPolicyType.STATIC.value:
                precedence_policy_type = ServiceBindingPolicyType.STATIC.value
            elif policy.type == ServiceBindingPolicyType.ENV_SPECIFIC.value:
                precedence_policy_type = ServiceBindingPolicyType.ENV_SPECIFIC.value
            else:
                raise ValueError("Invalid ServiceBindingPolicy type")

            if not dry_run:
                ServiceBindingPrecedencePolicy.objects.create(
                    service_id=precedence_policy.service_id,
                    service_type=get_service_type(service_obj),
                    tenant_id=precedence_policy.tenant_id,
                    priority=min_priority - 1,
                    cond_type=PrecedencePolicyCondType.ALWAYS_MATCH.value,
                    cond_data={},
                    type=precedence_policy_type,
                    data=plans,
                )
                # 删除 ServiceBindingPolicy
                policy.delete()
                # 创建 rule_based ServiceAllocationPolicy
                ServiceAllocationPolicy.objects.create(
                    service_id=precedence_policy.service_id,
                    tenant_id=precedence_policy.tenant_id,
                    type=ServiceAllocationPolicyType.RULE_BASED.value,
                )
            print(
                f"service {service_obj.name}:{service_obj.uuid},tenant_id {tenant_id}, "
                f"create always match precedence policy and rule based allocation policy"
                f"delete binding policy, "
            )

        # 根据孤立的 ServiceBindingPolicy 创建 uniform 类型的 ServiceAllocationPolicy
        for binding_policy in ServiceBindingPolicy.objects.all():
            service_obj = mixed_service_mgr.get(uuid=binding_policy.service_id)
            if not dry_run:
                ServiceAllocationPolicy.objects.create(
                    service_id=binding_policy.service_id,
                    tenant_id=binding_policy.tenant_id,
                    type=ServiceAllocationPolicyType.UNIFORM.value,
                )
            print(
                f"service {service_obj.uuid},tenant_id {binding_policy.tenant_id}, "
                f"create uniform allocation policy"
            )
