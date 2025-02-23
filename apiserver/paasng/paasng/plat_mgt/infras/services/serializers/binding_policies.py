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

import cattr
from rest_framework import serializers

from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    RuleBasedAllocationConfig,
    UnifiedAllocationConfig,
)
from paasng.accessories.servicehub.constants import PrecedencePolicyCondType


class BaseAllocationPolicySLZ(serializers.Serializer):
    plans = serializers.ListField(help_text="默认分配", child=serializers.CharField(), required=False)
    env_plans = serializers.DictField(
        help_text="按环境分配", child=serializers.ListField(child=serializers.CharField()), required=False
    )

    def validate(self, attrs):
        plans_exists = bool(attrs.get("plans"))
        env_plans_exists = bool(attrs.get("env_plans"))

        if plans_exists == env_plans_exists:
            raise serializers.ValidationError("Must provide either plans or env_plans, but not both.")


class AllocationPolicySLZ(BaseAllocationPolicySLZ):
    def to_internal_value(self, data) -> UnifiedAllocationConfig:
        return cattr.structure(super().to_internal_value(data), UnifiedAllocationConfig)


class AllocationPrecedencePolicySLZ(BaseAllocationPolicySLZ):
    cond_type = serializers.ChoiceField(choices=PrecedencePolicyCondType.get_choices())
    cond_data = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))
    priority = serializers.IntegerField()

    def to_internal_value(self, data) -> RuleBasedAllocationConfig:
        return cattr.structure(super().to_internal_value(data), RuleBasedAllocationConfig)


class PolicyCombinationConfigUpsertSLZ(serializers.Serializer):
    """
    Serializer for creating or updating a combination of policy configuration

    Special Context:
    - `service_id`: Provides the service_id for PolicyCombinationConfig
    """

    tenant_id = serializers.CharField(help_text="所属租户")
    allocation_precedence_policies = AllocationPrecedencePolicySLZ(many=True, help_text="规则分配配置")
    allocation_policy = AllocationPolicySLZ(help_text="统一分配配置")

    def to_internal_value(self, data) -> PolicyCombinationConfig:
        service_id = self.context.get("service_id")
        data["service_id"] = service_id
        return cattr.structure(super().to_internal_value(data), PolicyCombinationConfig)


class PolicyCombinationConfigOutputSLZ(serializers.Serializer):
    tenant_id = serializers.CharField(help_text="所属租户")
    service_id = serializers.CharField(help_text="服务 id")
    allocation_precedence_policies = AllocationPrecedencePolicySLZ(many=True, help_text="规则分配配置")
    allocation_policy = AllocationPolicySLZ(help_text="统一分配配置")


class DeletePolicyCombinationSLZ(serializers.Serializer):
    tenant_id = serializers.CharField(help_text="所属租户")
