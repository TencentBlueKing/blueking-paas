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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from paasng.platform.bkapp_model.constants import MAX_PROC_CPU, MAX_PROC_MEM
from paasng.platform.bkapp_model.models import ResQuotaPlan


class ResQuotaPlanOutputSLZ(serializers.Serializer):
    """资源配额方案序列化器"""

    id = serializers.IntegerField()
    plan_name = serializers.CharField()
    limits = serializers.DictField()
    requests = serializers.DictField()
    is_active = serializers.BooleanField()
    is_builtin = serializers.BooleanField()


class ResourceQuotaSLZ(serializers.Serializer):
    """资源配额序列化器 (用于 limits 和 requests)"""

    cpu = serializers.CharField()
    memory = serializers.CharField()

    def validate_cpu(self, value: str) -> str:
        """Validate CPU format: must end with 'm' and be a positive integer."""
        if not value.endswith("m"):
            raise serializers.ValidationError(_("必须以 'm' 为单位, 如 500m"))
        try:
            num = int(value[:-1])
            if num <= 0:
                raise serializers.ValidationError(_("必须为正整数, 如 500m"))
            if num > int(MAX_PROC_CPU[:-1]):
                raise serializers.ValidationError(_("不能超过最大值 %s") % MAX_PROC_CPU)
        except ValueError:
            raise serializers.ValidationError(_("格式不正确, 必须为正整数加 'm', 如 500m"))
        return value

    def validate_memory(self, value: str) -> str:
        """Validate memory format: must end with 'Mi' and be a positive integer."""
        if not value.endswith("Mi"):
            raise serializers.ValidationError(_("必须以 'Mi' 为单位, 如 512Mi"))
        try:
            num = int(value[:-2])
            if num <= 0:
                raise serializers.ValidationError(_("必须为正整数, 如 512Mi"))
            if num > int(MAX_PROC_MEM[:-2]):
                raise serializers.ValidationError(_("不能超过最大值 %s") % MAX_PROC_MEM)
        except ValueError:
            raise serializers.ValidationError(_("格式不正确, 必须为正整数加 'Mi', 如 512Mi"))
        return value


class ResQuotaPlanInputSLZ(serializers.Serializer):
    """资源配额方案基础输入序列化器"""

    plan_name = serializers.CharField(
        max_length=64,
        validators=[
            UniqueValidator(
                queryset=ResQuotaPlan.objects.all(),
                message=_("资源配额方案名称已存在，请使用其他名称"),
            )
        ],
    )
    limits = ResourceQuotaSLZ()
    requests = ResourceQuotaSLZ()
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        """Validate that requests do not exceed limits."""
        limits, requests = attrs["limits"], attrs["requests"]

        cpu_limits = int(limits["cpu"][:-1])
        cpu_requests = int(requests["cpu"][:-1])
        if cpu_requests > cpu_limits:
            raise serializers.ValidationError({"requests": {"cpu": _("cpu requests 不能超过 cpu limits")}})

        memory_limits = int(limits["memory"][:-2])
        memory_requests = int(requests["memory"][:-2])
        if memory_requests > memory_limits:
            raise serializers.ValidationError({"requests": {"memory": _("memory requests 不能超过 memory limits")}})

        return attrs
