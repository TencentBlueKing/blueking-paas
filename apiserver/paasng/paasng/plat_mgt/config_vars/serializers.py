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

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.engine.models.config_var import BuiltinConfigVar
from paasng.utils.validators import RE_CONFIG_VAR_KEY


class BuiltinConfigVarOutputSLZ(serializers.Serializer):
    """内建环境变量序列化器"""

    id = serializers.IntegerField(read_only=True, help_text="内建环境变量 ID")
    key = serializers.CharField(read_only=True, help_text="环境变量键")
    value = serializers.CharField(read_only=True, help_text="环境变量值")
    description = serializers.CharField(read_only=True, help_text="环境变量描述")
    operator = serializers.CharField(source="operator.username", read_only=True, help_text="操作人")
    updated = serializers.DateTimeField(read_only=True, help_text="最后更新时间")


class BuiltinConfigVarCreateInputSLZ(serializers.Serializer):
    """内建环境变量创建输入序列化器"""

    key = serializers.RegexField(
        RE_CONFIG_VAR_KEY,
        max_length=128,
        required=True,
        error_messages={"invalid": _("格式错误，只能以大写字母开头，由大写字母、数字与下划线组成。")},
        help_text="环境变量键",
    )
    value = serializers.CharField(max_length=512, required=True, help_text="环境变量值")
    description = serializers.CharField(max_length=512, required=True, help_text="环境变量描述")

    def validate_key(self, key: str) -> str:
        if BuiltinConfigVar.objects.filter(key=key).exists():
            raise ValidationError(_("内置环境变量 {key} 已存在").format(key=settings.CONFIGVAR_SYSTEM_PREFIX + key))
        return key


class BuiltinConfigVarUpdateInputSLZ(serializers.Serializer):
    """内建环境变量更新输入序列化器"""

    value = serializers.CharField(max_length=512, required=True, help_text="环境变量值")
    description = serializers.CharField(max_length=512, required=True, help_text="环境变量描述")
