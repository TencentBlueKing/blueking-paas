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

from django.utils.translation import gettext as _
from rest_framework import serializers

from paasng.platform.bkapp_model.constants import CPUResourceQuantity, MemoryResourceQuantity
from paasng.platform.bkapp_model.models import ResQuotaPlan
from paasng.platform.engine.constants import AppEnvName


class ResourcesQuantity(serializers.Serializer):
    """资源数量"""

    cpu = serializers.ChoiceField(choices=CPUResourceQuantity.get_choices())
    memory = serializers.ChoiceField(choices=MemoryResourceQuantity.get_choices())


class ResourcesSLZ(serializers.Serializer):
    """资源配置"""

    limits = ResourcesQuantity(help_text="资源限制", required=False, allow_null=True)
    requests = ResourcesQuantity(help_text="资源请求", required=False, allow_null=True)

    def validate(self, attrs):
        """Validate that requests does not exceed limits"""
        limits = attrs.get("limits")
        requests = attrs.get("requests")

        if not limits or not requests:
            return attrs

        # Validate CPU: requests should not exceed limits
        if CPUResourceQuantity(requests["cpu"]).exceeds(CPUResourceQuantity(limits["cpu"])):
            raise serializers.ValidationError(_("CPU requests 不能大于 limits"))

        # Validate Memory: requests should not exceed limits
        if MemoryResourceQuantity(requests["memory"]).exceeds(MemoryResourceQuantity(limits["memory"])):
            raise serializers.ValidationError(_("Memory requests 不能大于 limits"))

        return attrs


class PlanResourcesSLZ(serializers.Serializer):
    """资源配置 - 方案名称"""

    plan = serializers.CharField(help_text="资源配额方案名称")

    def validate_plan(self, value):
        """验证 plan 字段"""
        if not ResQuotaPlan.objects.filter(name=value, is_active=True).exists():
            raise serializers.ValidationError(_("资源配额方案 {plan} 不存在或未启用").format(plan=value))
        return value


# ============= Output Serializers =============


class EnvOverlayOutputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖输出序列化器"""

    plan_name = serializers.CharField(help_text="资源配额方案", allow_null=True)
    resources = serializers.JSONField(help_text="资源配置", allow_null=True)


class ProcessSpecOutputSLZ(serializers.Serializer):
    """单个进程规格输出序列化器"""

    name = serializers.CharField(help_text="进程名称")
    env_overlays = serializers.DictField(
        child=EnvOverlayOutputSLZ(), help_text="环境配置覆盖, key 为环境名称", required=False
    )


class ModuleProcessSpecOutputSLZ(serializers.Serializer):
    """模块进程规格输出序列化器"""

    module_name = serializers.CharField(help_text="模块名称")
    source_origin = serializers.IntegerField(help_text="源码来源")
    processes = serializers.ListField(child=ProcessSpecOutputSLZ(), help_text="进程规格列表")


# ============= Input Serializers =============


class EnvOverlayInputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖输入序列化器"""

    # 资源配额方案支持两种 json 格式:
    # 1. 直接指定方案名称, 如: {"plan": "4C2G"}
    # 2. 灵活设置资源限制和请求, 如: {"limits": {"cpu": "2", "memory": "2Gi"}, "requests": {"cpu": "1", "memory": "1Gi"} }
    resources = serializers.JSONField(help_text="资源配置", allow_null=True)

    def validate_resources(self, value):
        """验证 resources 字段"""
        if value is None:
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError(_("资源配置必须是一个字典"))

        if "plan" in value:
            slz_class = PlanResourcesSLZ
        else:
            slz_class = ResourcesSLZ

        slz = slz_class(data=value)
        if not slz.is_valid():
            raise serializers.ValidationError(slz.errors)
        return slz.validated_data


class ProcessSpecInputSLZ(serializers.Serializer):
    """单个进程规格更新序列化器"""

    env_overlays = serializers.DictField(
        child=EnvOverlayInputSLZ(), help_text="环境配置覆盖, key 为环境名称", required=True
    )

    def validate_env_overlays(self, value):
        """验证 env_overlays 的 key 必须是有效的环境名称"""
        valid_env_names = AppEnvName.get_values()
        invalid_keys = [key for key in value if key not in valid_env_names]

        if invalid_keys:
            raise serializers.ValidationError(
                _("无效的环境名称: {invalid_keys}, 有效值为: {valid_keys}").format(
                    invalid_keys=", ".join(invalid_keys),
                    valid_keys=", ".join(valid_env_names),
                )
            )

        return value
