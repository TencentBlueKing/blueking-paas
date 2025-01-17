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

from rest_framework import serializers

from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    RuleBasedAllocationConfig,
    UnifiedAllocationConfig,
)
from paasng.accessories.servicehub.constants import COND_TYPE_TO_DATA_KEY_MAP, PrecedencePolicyCondType


class BaseAllocationConfigSLZ(serializers.Serializer):
    plans = serializers.ListField(child=serializers.CharField(), required=False)
    env_plans = serializers.DictField(
        help_text="按环境分配", child=serializers.ListField(child=serializers.CharField()), required=False
    )

    def validate(self, attrs):
        plans_exist = attrs.get("plans") is not None and len(attrs.get("plans")) > 0
        env_plans_exist = attrs.get("env_plans") is not None and len(attrs.get("env_plans")) > 0

        if plans_exist == env_plans_exist:
            raise serializers.ValidationError("Both plans and env_plans cannot exist together or be absent together.")


class UnifiedAllocationConfigSLZ(BaseAllocationConfigSLZ):
    def to_internal_value(self, data) -> UnifiedAllocationConfig:
        return UnifiedAllocationConfig(**super().to_internal_value(data))


class RuleBasedAllocationConfigSLZ(BaseAllocationConfigSLZ):
    cond_type = serializers.ChoiceField(choices=PrecedencePolicyCondType.get_choices())
    cond_data = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))
    priority = serializers.IntegerField()

    def validate_cond_data(self, value):
        cond_type = self.initial_data.get("cond_type")
        cond_data_key = COND_TYPE_TO_DATA_KEY_MAP[cond_type]
        if cond_data_key not in value:
            raise serializers.ValidationError(f"cond_data need key {cond_data_key} when cond_type is {cond_type}")

        return value

    def to_internal_value(self, data) -> RuleBasedAllocationConfig:
        return RuleBasedAllocationConfig(**super().to_internal_value(data))


class PolicyCombinationConfigSLZ(serializers.Serializer):
    tenant_id = serializers.CharField(help_text="所属租户")
    rule_based_allocation_configs = RuleBasedAllocationConfigSLZ(many=True, help_text="规则分配配置")
    unified_allocation_config = UnifiedAllocationConfigSLZ(help_text="统一分配配置")

    def to_internal_value(self, data) -> PolicyCombinationConfig:
        return PolicyCombinationConfig(**super().to_internal_value(data))


class DeletePolicyCombinationSLZ(serializers.Serializer):
    tenant_id = serializers.CharField(help_text="所属租户")
