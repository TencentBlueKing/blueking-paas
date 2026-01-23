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

import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from paasng.platform.bkapp_model.constants import MAX_PROC_CPU, MAX_PROC_MEM
from paasng.platform.bkapp_model.models import ResQuotaPlan

CPU_PATTERN = re.compile(r"^([1-9][0-9]*)(m)$")
MEMORY_PATTERN = re.compile(r"^([1-9][0-9]*)(Mi|Gi)$")


class ResQuotaPlanOutputSLZ(serializers.Serializer):
    """资源配额方案序列化器"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    limits = serializers.DictField()
    requests = serializers.DictField()
    is_active = serializers.BooleanField()
    is_builtin = serializers.BooleanField()


class ResourceQuotaSLZ(serializers.Serializer):
    """资源配额序列化器 (用于 limits 和 requests)"""

    cpu = serializers.CharField()
    memory = serializers.CharField()

    class Meta:
        ref_name = "plat_mgt.ResourceQuotaSLZ"

    def validate_cpu(self, value: str) -> str:
        """Validate CPU format: must end with 'm' and be a positive integer."""

        try:
            current_m = parse_cpu_to_millicores(value)
        except ValueError:
            raise serializers.ValidationError(_("格式不正确, 必须为正整数加 'm'"))

        max_m = parse_cpu_to_millicores(MAX_PROC_CPU)
        if current_m > max_m:
            raise serializers.ValidationError(_("不能超过最大值 %s") % MAX_PROC_CPU)

        return value

    def validate_memory(self, value: str) -> str:
        """Validate memory format: must end with 'Mi' or 'Gi' and be a positive integer."""

        try:
            current_mi = parse_memory_to_mi(value)
        except ValueError:
            raise serializers.ValidationError(_("格式不正确, 必须为正整数加 'Mi' 或 'Gi'"))

        max_mi = parse_memory_to_mi(MAX_PROC_MEM)
        if current_mi > max_mi:
            raise serializers.ValidationError(_("不能超过最大值 %s") % MAX_PROC_MEM)

        return value


class ResQuotaPlanInputSLZ(serializers.Serializer):
    """资源配额方案基础输入序列化器"""

    name = serializers.RegexField(
        regex=r"^[a-zA-Z0-9]+$",
        max_length=64,
        validators=[
            UniqueValidator(queryset=ResQuotaPlan.objects.all(), message=_("资源配额方案名称已存在，请使用其他名称"))
        ],
        error_messages={"invalid": _("名称只能包含数字和英文字符")},
    )
    limits = ResourceQuotaSLZ()
    requests = ResourceQuotaSLZ()
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        """Validate that requests do not exceed limits."""
        limits, requests = attrs["limits"], attrs["requests"]

        cpu_limits = parse_cpu_to_millicores(limits["cpu"])
        cpu_requests = parse_cpu_to_millicores(requests["cpu"])
        if cpu_requests > cpu_limits:
            raise serializers.ValidationError({"requests": {"cpu": _("cpu requests 不能超过 cpu limits")}})

        memory_limits = parse_memory_to_mi(limits["memory"])
        memory_requests = parse_memory_to_mi(requests["memory"])
        if memory_requests > memory_limits:
            raise serializers.ValidationError({"requests": {"memory": _("memory requests 不能超过 memory limits")}})

        return attrs


def parse_memory_to_mi(memory_str: str) -> int:
    """Parse Kubernetes memory string to Mi."""
    match = MEMORY_PATTERN.match(memory_str)
    if not match:
        raise ValueError(_("格式不正确, 必须为正整数加 'Mi' 或 'Gi'"))

    value, unit = match.groups()
    value = int(value)

    return value if unit == "Mi" else value * 1024


def parse_cpu_to_millicores(cpu_str: str) -> int:
    """Parse Kubernetes CPU string to m."""
    match = CPU_PATTERN.match(cpu_str)
    if not match:
        raise ValueError(_("格式不正确, 必须为正整数加 'm'"))

    return int(match.group(1))
