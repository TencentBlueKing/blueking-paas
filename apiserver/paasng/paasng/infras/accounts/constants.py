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

from typing import Dict, cast

from aenum import extend_enum, skip
from blue_krill.data_types.enum import FeatureFlagField
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.utils.basic import ChoicesEnum


class SiteRole(ChoicesEnum):
    NOBODY = 1
    USER = 2
    ADMIN = 3
    SUPER_USER = 4
    BANNED_USER = 5

    PLATFORM_MANAGER = 20
    APP_TEMPLATES_MANAGER = 21
    PLATFORM_OPERATOR = 22

    _choices_labels = (
        (NOBODY, _("没有特定角色的用户")),
        (USER, _("普通用户")),
        (ADMIN, _("管理员")),
        (SUPER_USER, _("超级用户")),
        (BANNED_USER, _("不允许访问服务的用户")),
        (PLATFORM_MANAGER, _("平台管理员")),
        (APP_TEMPLATES_MANAGER, _("应用模板管理员")),
        (PLATFORM_OPERATOR, _("平台运营人员")),
    )


class AccountFeatureFlag(ChoicesEnum):
    """
    Account feature 常量表
    """

    ALLOW_ADVANCED_CREATION_OPTIONS = "ALLOW_ADVANCED_CREATION_OPTIONS"
    ENABLE_WEB_CONSOLE = "ENABLE_WEB_CONSOLE"
    ALLOW_CREATE_SMART_APP = "ALLOW_CREATE_SMART_APP"
    ALLOW_PLUGIN_CENTER = "ALLOW_PLUGIN_CENTER"
    ALLOW_AI_ASSISTANT = "ALLOW_AI_ASSISTANT"

    _choices_labels = [
        (ALLOW_ADVANCED_CREATION_OPTIONS, _("允许创建模块时使用高级选项")),
        # 加密镜像：镜像 label 设置了 secureEncrypted=1 的镜像
        (ENABLE_WEB_CONSOLE, _("允许打开未加密镜像的访问控制台")),
        (ALLOW_CREATE_SMART_APP, _("允许创建 SMart 应用")),
        (ALLOW_PLUGIN_CENTER, _("允许使用插件开发者中心")),
        (ALLOW_AI_ASSISTANT, _("允许使用 AI 助手")),
    ]

    _defaults = skip(
        {
            ALLOW_ADVANCED_CREATION_OPTIONS: False,
            ENABLE_WEB_CONSOLE: False,
            ALLOW_AI_ASSISTANT: False,
            ALLOW_CREATE_SMART_APP: settings.IS_ALLOW_CREATE_SMART_APP_BY_DEFAULT,
            ALLOW_PLUGIN_CENTER: settings.IS_ALLOW_PLUGIN_CENTER,
        }
    )

    @classmethod
    def get_default_flags(cls) -> Dict[str, bool]:
        """Get the default user feature flags, client is sage to modify the result because it's a copy"""
        flags = cast(Dict, cls._defaults)
        return flags.copy()

    @classmethod
    def register_ext_feature_flag(cls, feature_flag: FeatureFlagField) -> None:
        """注册额外的用户特性到枚举类中"""
        name, label, default = feature_flag.name, feature_flag.label, feature_flag.default
        # 无名的不允许注册
        if not name:
            raise ValueError("feature flag's name can not be empty.")

        # 已经注册过的，需要跳过
        if getattr(cls, name, None):
            return

        extend_enum(cls, name, name)
        cls._choices_labels.value.append((name, label))
        cls._defaults[name] = default  # type: ignore


class FunctionType(ChoicesEnum):
    """
    用到短信验证码的功能, 避免字符串硬编码
    """

    DEFAULT = "default"
    SVN = "SVN"
    GET_APP_SECRET = "GET_APP_SECRET"
    RETRIEVE_UNBOUND_SERVICE_SENSITIVE_FIELD = "RETRIEVE_UNBOUND_SERVICE_SENSITIVE_FIELD"


FUNCTION_TYPE_MAP = {
    FunctionType.SVN.value: "verification_code",
    FunctionType.GET_APP_SECRET.value: "app_secret_vcode_storage_key",
}
