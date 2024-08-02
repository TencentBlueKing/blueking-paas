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

import shlex
from typing import Any, Dict, Optional, Tuple, Type

import cattr
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accessories.publish.market.serializers import ProductTagByNameField
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.serializers import AppIDSMartField, AppNameField
from paasng.platform.bkapp_model.entities import Addon, v1alpha2
from paasng.platform.declarative import constants
from paasng.platform.declarative.application.resources import ApplicationDesc, DisplayOptions, MarketDesc
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.utils import get_quota_plan
from paasng.utils.i18n.serializers import I18NExtend, i18n
from paasng.utils.serializers import Base64FileField


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


@i18n
class SMartV1DescriptionSLZ(serializers.Serializer):
    """Serializer for parsing the origin version of S-Mart application description"""

    # For some reason, the max length for the `app_code` field uses the legacy value of 16
    # in the v1 schema, the value is changed to 20 in later versions.
    app_code = AppIDSMartField(max_length=16)
    app_name = I18NExtend(AppNameField())
    version = serializers.RegexField(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$", required=True, help_text="版本")
    # Celery 相关
    is_use_celery = serializers.BooleanField(required=True, help_text="是否启用 celery")
    is_use_celery_with_gevent = serializers.BooleanField(
        required=False, help_text="是否启用 celery (gevent)模式", default=False
    )
    is_use_celery_beat = serializers.BooleanField(required=False, help_text="是否启用 celery beat", default=False)
    author = serializers.CharField(required=True, help_text="应用作者")
    introduction = I18NExtend(serializers.CharField(required=True, help_text="简介"))

    # Not required fields
    category = ProductTagByNameField(required=False, source="tag")
    language = serializers.CharField(
        required=False, help_text="开发语言", default=AppLanguage.PYTHON.value, validators=[validate_language]
    )
    desktop = DesktopOptionsSLZ(required=False, default=DesktopOptionsSLZ.gen_default_value, help_text="桌面展示选项")
    env = serializers.ListField(child=LegacyEnvVariableSLZ(), required=False, default=list)
    container = ContainerSpecSLZ(required=False, allow_null=True, source="package_plan")
    libraries = serializers.ListField(child=LibrarySLZ(), required=False, default=list)
    logo_b64data = Base64FileField(required=False, help_text="logo", source="logo")

    def to_internal_value(self, data) -> Tuple[ApplicationDesc, DeploymentDesc]:
        attrs = super().to_internal_value(data)
        market_desc = MarketDesc(
            introduction_en=attrs["introduction_en"],
            introduction_zh_cn=attrs["introduction_zh_cn"],
            display_options=attrs.get("desktop"),
            logo=attrs.get("logo", constants.OMITTED_VALUE),
        )
        if attrs.get("tag"):
            market_desc.tag_id = attrs["tag"].id

        package_plan = get_quota_plan(attrs.get("package_plan")) if attrs.get("package_plan") else None
        addons = [Addon(name=service) for service in settings.SMART_APP_DEFAULT_SERVICES_CONFIG]
        processes = [
            {
                "name": "web",
                "args": shlex.split(constants.WEB_PROCESS),
                "res_quota_plan": package_plan,
                "replicas": 1,
                "proc_command": constants.WEB_PROCESS,
            }
        ]
        is_use_celery = False
        if attrs["is_use_celery"]:
            is_use_celery = True
            addons.append(Addon(name="rabbitmq"))
            processes.append(
                {
                    "name": "celery",
                    "args": shlex.split(constants.CELERY_PROCESS),
                    "res_quota_plan": package_plan,
                    "replicas": 1,
                    "proc_command": constants.CELERY_PROCESS,
                }
            )
        elif attrs["is_use_celery_with_gevent"]:
            is_use_celery = True
            addons.append(Addon(name="rabbitmq"))
            processes.append(
                {
                    "name": "celery",
                    "args": shlex.split(constants.CELERY_PROCESS_WITH_GEVENT),
                    "res_quota_plan": package_plan,
                    "replicas": 1,
                    "proc_command": constants.CELERY_PROCESS_WITH_GEVENT,
                }
            )

        if attrs["is_use_celery_beat"]:
            if not is_use_celery:
                raise ValueError("Can't use celery beat but not use celery.")
            processes.append(
                {
                    "name": "beat",
                    "args": shlex.split(constants.CELERY_BEAT_PROCESS),
                    "res_quota_plan": package_plan,
                    "replicas": 1,
                    "proc_command": constants.CELERY_BEAT_PROCESS,
                }
            )

        plugins = [
            dict(type=constants.AppDescPluginType.APP_VERSION, data=attrs["version"]),
            dict(type=constants.AppDescPluginType.APP_LIBRARIES, data=attrs["libraries"]),
        ]

        spec = v1alpha2.BkAppSpec(
            processes=processes,
            configuration={"env": [{"name": item["key"], "value": item["value"]} for item in attrs.get("env", [])]},
            addons=addons,
        )
        application_desc = ApplicationDesc(
            spec_version=constants.AppSpecVersion.VER_1,
            code=attrs["app_code"],
            name_en=attrs["app_name_en"],
            name_zh_cn=attrs["app_name_zh_cn"],
            market=market_desc,
            modules={
                "default": {
                    "name": "default",
                    "is_default": True,
                    "services": [{"name": addon.name} for addon in addons],
                }
            },
            plugins=plugins,
            instance_existed=bool(self.instance),
        )
        deployment_desc = cattr.structure(
            {"spec": spec, "language": attrs.get("language"), "spec_version": constants.AppSpecVersion.VER_1},
            DeploymentDesc,
        )
        return application_desc, deployment_desc
