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

from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.platform.engine.models.config_var import BuiltinConfigVar
from paasng.platform.engine.serializers import ConfigVarSLZ as BaseConfigVarSLZ
from paasng.utils.validators import RE_CONFIG_VAR_KEY


class ConfigVarSLZ(BaseConfigVarSLZ):
    module_display = ModuleSLZ(required=False, source="module", read_only=True)
    key = serializers.RegexField(
        RE_CONFIG_VAR_KEY,
        max_length=1024,
        required=True,
        error_messages={"invalid": _("格式错误，只能以大写字母开头，由大写字母、数字与下划线组成。")},
    )


class BuiltinConfigVarCreateInputSLZ(serializers.Serializer):
    key = serializers.RegexField(
        RE_CONFIG_VAR_KEY,
        max_length=128,
        required=True,
        error_messages={"invalid": _("格式错误，只能以大写字母开头，由大写字母、数字与下划线组成。")},
    )
    value = serializers.CharField(max_length=512, required=True)
    description = serializers.CharField(max_length=512, required=True, help_text="变量描述")

    def validate_key(self, key: str) -> str:
        if BuiltinConfigVar.objects.filter(key=key).exists():
            raise ValidationError(_("内置环境变量 {key} 已存在").format(key=settings.CONFIGVAR_SYSTEM_PREFIX + key))
        return key


class BuiltinConfigVarUpdateInputSLZ(serializers.Serializer):
    value = serializers.CharField(max_length=512, required=True)
    description = serializers.CharField(max_length=512, required=True, help_text="变量描述")


class BuiltinConfigVarListOutputSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    key = serializers.CharField()
    value = serializers.CharField()
    description = serializers.CharField()
    updated = serializers.DateTimeField()
    operator = serializers.SerializerMethodField()

    def get_operator(self, obj):
        return obj.operator.username
