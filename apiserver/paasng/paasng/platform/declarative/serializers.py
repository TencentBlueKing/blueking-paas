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

from typing import Any, Dict, List, Optional, Type

import cattr
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.constants import AppLanguage
from paasng.platform.declarative.application.resources import DisplayOptions
from paasng.platform.declarative.deployment.resources import ProcfileProc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH, PROC_TYPE_PATTERN


def validate_desc(
    serializer: Type[serializers.Serializer],
    data: Dict,
    instance: Optional[Any] = None,
    context: Optional[Dict] = None,
    partial: Optional[bool] = None,
) -> Any:
    """Use serializer to validate a given structure, the exception was transformed

    :partial: Perform partial updates(aka PATCH), by default, this value is True when instance was provided.
        In this case, all fields with default value configured will not be written into validated data.
    :raises: DescriptionValidationError when input is invalid
    """
    if partial is None:
        partial = instance is not None
    slz = serializer(data=data, instance=instance, context=context or dict(), partial=partial)
    try:
        slz.is_valid(raise_exception=True)
    except ValidationError as e:
        raise DescriptionValidationError.from_validation_error(e)
    return slz.validated_data


def validate_language(language: str) -> AppLanguage:
    """校验 AppLanguage

    Q: 为什么不直接使用 AppLanguage.get_django_choices() 来限制输入参数？
    A: 因为我们会认为 NodeJS, nodejs, NODEJS 都是值 AppLanguage.NodeJS. 使用 AppLanguage._missing_ 允许更高的容错性.
    """
    try:
        return AppLanguage(language)
    except ValueError:
        raise serializers.ValidationError(f"'{language}' is not a supported language.")


class UniConfigSLZ(serializers.Serializer):
    """Serializer for validate universal app config file"""

    app_version = serializers.CharField(required=False)
    spec_version = serializers.IntegerField(required=False)
    # NOTE: 这个 app 实际上是 AppDescriptionSLZ
    app = serializers.JSONField(required=False, default={}, help_text="App-related config fields")
    modules = serializers.JSONField(required=False, default={}, help_text="Modules-related config fields")
    module = serializers.JSONField(required=False, default={}, help_text="Deploy-related config fields")


# Serializers for S-Mart App


class DesktopOptionsSLZ(serializers.Serializer):
    """Serializer for validating application's market display options"""

    width = serializers.IntegerField(help_text="窗口宽度", required=False, default=1280)
    height = serializers.IntegerField(help_text="窗口高度", required=False, default=600)
    is_max = serializers.BooleanField(default=False, source="is_win_maximize", help_text="是否最大化")
    is_display = serializers.BooleanField(default=True, source="visible", help_text="是否在桌面展示")

    @classmethod
    def gen_default_value(cls) -> DisplayOptions:
        """Generate default `DisplayOptions` object"""
        attrs = serializers.Serializer.to_internal_value(cls(), {})
        return DisplayOptions(**attrs)

    def to_internal_value(self, data) -> DisplayOptions:
        attrs = super().to_internal_value(data)
        return DisplayOptions(**attrs)


class ContainerSpecSLZ(serializers.Serializer):
    """Serializer for validating application's container specification"""

    memory = serializers.IntegerField(help_text="内存容量, 单位 Mi", default=1024)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        memory = attrs.pop("memory", 1024)
        if memory > 2048:
            return settings.ULTIMATE_PROC_SPEC_PLAN
        if memory > 1024:
            return settings.PREMIUM_PROC_SPEC_PLAN
        else:
            return settings.DEFAULT_PROC_SPEC_PLAN


class LibrarySLZ(serializers.Serializer):
    """Serializer for validating applications's libraries"""

    name = serializers.CharField(help_text="依赖库名称", required=True)
    version = serializers.CharField(help_text="依赖库版本", required=True)


class LegacyEnvVariableSLZ(serializers.Serializer):
    """Legacy env variable serializer, only allow keys which starts with 'BK_APP_'"""

    key = serializers.RegexField(
        r"^BKAPP_[A-Z0-9_]+$",
        max_length=50,
        required=True,
        error_messages={"invalid": _('格式错误，只能以 "BKAPP_" 开头，由大写字母、数字与下划线组成，长度不超过 50。')},
    )
    value = serializers.CharField(required=True, max_length=1000)


def validate_procfile_procs(data: Dict[str, str]) -> List[ProcfileProc]:
    """Validate process data which was read from procfile.

    :param data: Processes data, format: {proc_type: command}
    :return: Validated process list
    :raise DescriptionValidationError: When the data is not valid
    """
    if len(data) > settings.MAX_PROCESSES_PER_MODULE:
        raise DescriptionValidationError(
            f"The number of processes exceeded: maximum {settings.MAX_PROCESSES_PER_MODULE} processes per module, "
            + f"but got {len(data)}"
        )

    for proc_type in data:
        if not PROC_TYPE_PATTERN.match(proc_type):
            raise DescriptionValidationError(
                f"Invalid proc type: {proc_type}, must match pattern {PROC_TYPE_PATTERN.pattern}"
            )
        if len(proc_type) > PROC_TYPE_MAX_LENGTH:
            raise DescriptionValidationError(
                f"Invalid proc type: {proc_type}, must not longer than {PROC_TYPE_MAX_LENGTH} characters"
            )

    # Formalize processes data and return
    try:
        return cattr.structure(
            [{"name": name.lower(), "command": command} for name, command in data.items()],
            List[ProcfileProc],
        )
    except KeyError as e:
        raise DescriptionValidationError(f"Invalid process data, missing: {e}")
    except ValueError as e:
        raise DescriptionValidationError(f"Invalid process data, {e}")
