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

from paas_wl.bk_app.cnative.specs.models import ResQuotaPlan
from paasng.platform.bkapp_model.constants import CPUResourceQuantity, MemoryResourceQuantity


class ResQuotaPlanOutputSLZ(serializers.Serializer):
    """资源配额方案序列化器"""

    id = serializers.IntegerField()
    plan_name = serializers.CharField()
    cpu_limit = serializers.CharField()
    memory_limit = serializers.CharField()
    cpu_request = serializers.CharField()
    memory_request = serializers.CharField()
    is_active = serializers.BooleanField()
    is_builtin = serializers.BooleanField()


class ResQuotaPlanBaseInputSLZ(serializers.Serializer):
    """资源配额方案基础输入序列化器"""

    plan_name = serializers.CharField(max_length=64)
    cpu_limit = serializers.ChoiceField(choices=CPUResourceQuantity.get_choices())
    memory_limit = serializers.ChoiceField(choices=MemoryResourceQuantity.get_choices())
    cpu_request = serializers.ChoiceField(choices=CPUResourceQuantity.get_choices())
    memory_request = serializers.ChoiceField(choices=MemoryResourceQuantity.get_choices())
    is_active = serializers.BooleanField(required=False, default=True)


class ResQuotaPlanCreateInputSLZ(ResQuotaPlanBaseInputSLZ):
    """资源配额方案创建输入序列化器"""

    def validate_plan_name(self, value):
        if ResQuotaPlan.objects.filter(plan_name=value).exists():
            raise serializers.ValidationError("资源配额方案名称已存在，请使用其他名称")
        return value


class ResQuotaPlanUpdateInputSLZ(ResQuotaPlanBaseInputSLZ):
    """资源配额方案更新输入序列化器"""

    def validate_plan_name(self, value):
        # 排除自身实例
        if ResQuotaPlan.objects.filter(plan_name=value).exclude(id=self.context["pk"]).exists():
            raise serializers.ValidationError("资源配额方案名称已存在，请使用其他名称")
        return value
