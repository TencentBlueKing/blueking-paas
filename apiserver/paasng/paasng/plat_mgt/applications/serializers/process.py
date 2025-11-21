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

    plan_name = serializers.CharField(help_text="资源配额方案", allow_null=True)
    resources = ResourcesSLZ(help_text="资源配置", allow_null=True)


class EnvOverlayInputSLZ(serializers.Serializer):
    """进程规格环境配置覆盖输入序列化器"""

    plan_name = serializers.ChoiceField(
        help_text="资源配额方案",
        choices=ResQuotaPlan.get_choices(),
        allow_null=True,
        required=False,
    )
    resources = ResourcesSLZ(help_text="资源配置", allow_null=True, required=False)

    def validate(self, attrs):
        """验证: plan_name 和 resources 互斥，必须提供其中一个"""
        plan_name = attrs.get("plan_name")
        resources = attrs.get("resources")

        # 两者都没有提供
        if plan_name is None and resources is None:
            raise serializers.ValidationError(_("必须提供 plan_name 或 resources 其中之一"))

        # 两者都提供了
        if plan_name is not None and resources is not None:
            raise serializers.ValidationError(_("plan_name 和 resources 不能同时指定，请选择其一"))

        return attrs


class ProcessSpecOutputSLZ(serializers.Serializer):
    """单个进程规格输出序列化器"""

    name = serializers.CharField(help_text="进程名称")
    env_overlays = serializers.DictField(
        child=EnvOverlayOutputSLZ(), help_text="环境配置覆盖, key 为环境名称", required=False
    )


class ProcessSpecInputSLZ(serializers.Serializer):
    """单个进程规格更新序列化器"""

    env_overlays = serializers.DictField(
        child=EnvOverlayInputSLZ(), help_text="环境配置覆盖, key 为环境名称", required=True
    )


class ModuleProcessSpecOutputSLZ(serializers.Serializer):
    """模块进程规格输出序列化器"""

    module_name = serializers.CharField(help_text="模块名称")
    source_origin = serializers.IntegerField(help_text="源码来源")
    processes = serializers.ListField(child=ProcessSpecOutputSLZ(), help_text="进程规格列表")
