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
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.core.region.models import get_all_regions
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.engine.configurations.config_var import get_default_builtin_config_vars
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
        max_length=1024,
        required=True,
        error_messages={"invalid": _("格式错误，只能以大写字母开头，由大写字母、数字与下划线组成。")},
    )
    value = serializers.CharField(required=True)
    description = serializers.CharField(max_length=200, required=True, help_text="变量描述")

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if BuiltinConfigVar.objects.filter(key=data["key"]).exists():
            raise ValidationError(_("名称为 {key} 的变量已经存在，不能重复添加。").format(key=data["key"]))

        # region 和 environment 不影响默认内置环境变量的 key
        region = list(get_all_regions().keys())[0]
        environment = AppEnvironment.PRODUCTION.value
        if data["key"] in get_default_builtin_config_vars(region, environment).keys():  # noqa: SIM118
            raise ValidationError(_("名称为 {key} 的变量已存在于系统内置变量，不能添加。").format(key=data["key"]))

        return data


class BuiltinConfigVarCreateOutputSLZ(serializers.Serializer):
    id = serializers.IntegerField()


class BuiltinConfigVarUpdateInputSLZ(serializers.Serializer):
    value = serializers.CharField(required=True)
    description = serializers.CharField(max_length=200, required=True, help_text="变量描述")


class BuiltinConfigVarListInputSLZ(serializers.Serializer):
    region = serializers.ChoiceField(choices=[(region, region) for region in list(get_all_regions().keys())])

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data["region"] not in list(get_all_regions().keys()):
            raise ValidationError(_("无法找到指定的region: {region}").format(region=data["region"]))
        return data


class BuiltinConfigVarListOutputSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    key = serializers.CharField()
    value = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    updated = serializers.DateTimeField()
    updater = serializers.CharField()
