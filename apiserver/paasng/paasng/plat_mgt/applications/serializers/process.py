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

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paasng.platform.bkapp_model.constants import CPUResourceQuantity, MemoryResourceQuantity


class ResourcesQuantity(serializers.Serializer):
    """资源数量"""

    cpu = serializers.ChoiceField(choices=CPUResourceQuantity.get_choices())
    memory = serializers.ChoiceField(choices=MemoryResourceQuantity.get_choices())


class ResourcesSLZ(serializers.Serializer):
    """资源配置"""

    limits = ResourcesQuantity(help_text="资源限制", required=False, allow_null=True)
    requests = ResourcesQuantity(help_text="资源请求", required=False, allow_null=True)


class EnvOverlayOutputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖序列化器"""

    plan_name = serializers.SerializerMethodField(help_text="资源配额方案")
    resources = ResourcesSLZ(help_text="资源配置", allow_null=True)

    def get_plan_name(self, obj):
        """当 resources 不为 None 时返回 custom"""
        if obj["resources"] is not None:
            return "custom"
        return obj["plan_name"]


class EnvOverlayInputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖输入序列化器"""

    plan_name = serializers.ChoiceField(
        help_text="资源配额方案",
        choices=ResQuotaPlan.get_choices() + [("custom", "custom")],
    )
    resources = ResourcesSLZ(help_text="资源配置", allow_null=True)

    def validate(self, attrs):
        """验证: 只有当 plan_name 为 custom 时才接受 resources"""
        plan_name = attrs["plan_name"]
        resources = attrs["resources"]

        # 如果提供了 resources, 则 plan_name 必须为 custom
        if resources is not None and plan_name != "custom":
            raise serializers.ValidationError({"plan_name": _("当指定自定义资源配置时, plan_name 必须为 'custom'")})

        # 如果 plan_name 为 custom, 则必须提供 resources
        if plan_name == "custom" and resources is None:
            raise serializers.ValidationError({"resources": _("当 plan_name 为 'custom' 时, 必须提供资源配置")})

        return attrs


class ProcessEnvOverlayOutputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖输出序列化器"""

    name = serializers.CharField(help_text="进程名称")
    env_overlays = serializers.DictField(
        child=EnvOverlayOutputSLZ(), help_text="环境配置覆盖, key 为环境名称", required=False
    )


class ProcessEnvOverlayInputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖输入序列化器"""

    name = serializers.CharField(help_text="进程名称")
    env_overlays = serializers.DictField(
        child=EnvOverlayInputSLZ(), help_text="环境配置覆盖, key 为环境名称", required=False
    )


class ModuleProcessSpecOutputSLZ(serializers.Serializer):
    """模块进程规格输出序列化器"""

    module_name = serializers.CharField(help_text="模块名称")
    source_origin = serializers.IntegerField(help_text="源码来源")
    processes = serializers.ListField(child=ProcessEnvOverlayOutputSLZ(), help_text="进程规格列表")


class ModuleProcessSpecInputSLZ(serializers.Serializer):
    """模块进程规格更新序列化器"""

    module_name = serializers.CharField(help_text="模块名称")
    source_origin = serializers.IntegerField(help_text="源码来源")
    processes = serializers.ListField(child=ProcessEnvOverlayInputSLZ(), help_text="进程规格列表")
