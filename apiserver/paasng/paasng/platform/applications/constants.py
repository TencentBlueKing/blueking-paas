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

from typing import Type

from blue_krill.data_types.enum import EnumField, FeatureFlag, FeatureFlagField, IntStructuredEnum, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class ApplicationType(StrStructuredEnum):
    DEFAULT = EnumField("default", label="普通应用")  # 默认类型：无任何定制逻辑
    ENGINELESS_APP = EnumField(
        "engineless_app", label="外链应用"
    )  # 无引擎应用：不部署，但可通过设置第三方地址上线到市场，也支持申请云 API
    # 云原生架构应用：完全基于 YAML 模型的应用，当前作为一个独立应用类型存在，但未来它也许会成为所有应用
    # （比如基于 buildpack 的“普通应用”）统一底层架构。到那时，再来考虑如何处置这个类型吧
    CLOUD_NATIVE = EnumField("cloud_native", label="云原生应用")


class ApplicationRole(IntStructuredEnum):
    NOBODY = EnumField(-1, label="无身份用户")
    COLLABORATOR = EnumField(1, label="协作者")
    ADMINISTRATOR = EnumField(2, label="管理员")
    DEVELOPER = EnumField(3, label="开发")
    OPERATOR = EnumField(4, label="运营")

    @classmethod
    def get_roles(cls: Type[IntStructuredEnum]):
        return [
            {"id": role.value, "name": role.name.lower()}
            for role in cls
            if role.name not in ["COLLABORATOR", "_choices_labels"]
        ]


class AppLanguage(StrStructuredEnum):
    PYTHON = EnumField("Python", label="Python")
    PHP = EnumField("PHP", label="PHP")
    GO = EnumField("Go", label="Go")
    NODEJS = EnumField("NodeJS", label="NodeJS")
    JAVA = EnumField("Java", label="Java")

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return super()._missing_(value)
        # 保证不同格式的 language 都可以正常转换到 AppLanguage
        maps = {"python": cls.PYTHON, "php": cls.PHP, "go": cls.GO, "nodejs": cls.NODEJS, "java": cls.JAVA}
        return maps.get(value.lower()) or super()._missing_(value)

    def __str__(self):
        return self.get_choice_label(self)


LEVEL_PARAM_DICT = {
    "20x": ["200", "201", "202", "204", "205", "206"],
    "30x": ["300", "301", "302", "303", "304", "305", "307"],
    "40x": ["400", "401", "402", "403", "404", "405"],
    "50x": ["500", "501", "502", "503", "504"],
}


class AppEnvironment(StrStructuredEnum):
    STAGING = EnumField("stag", label="预发布环境")
    PRODUCTION = EnumField("prod", label="生产环境")


class AppFeatureFlag(FeatureFlag):  # type: ignore
    """App feature 常量表"""

    RELEASE_TO_WEIXIN_QIYE = FeatureFlagField(label="发布移动端微信企业号(企业微信)")
    ACCESS_CONTROL_EXEMPT_MODE = FeatureFlagField(label="访问控制豁免模式")
    # 数据统计相关的 feature flag
    PA_WEBSITE_ANALYTICS = FeatureFlagField(label="网站访问统计功能")
    PA_CUSTOM_EVENT_ANALYTICS = FeatureFlagField(label="自定义事件统计功能")
    PA_INGRESS_ANALYTICS = FeatureFlagField(label="访问日志统计功能")

    APPLICATION_DESCRIPTION = FeatureFlagField(label="部署时使用应用描述文件", default=True)
    MODIFY_ENVIRONMENT_VARIABLE = FeatureFlagField(
        label="修改环境变量，已迁移到插件开发者中心的应用不允许修改环境变量", default=True
    )
    ENABLE_BK_LOG_COLLECTOR = FeatureFlagField(label=_("使用蓝鲸日志平台方案采集日志"), default=False)

    TOGGLE_EGRESS_BINDING = FeatureFlagField(label=_("开启出口 IP 管理"), default=False)

    # 持久存储挂载卷相关的 feature flag
    ENABLE_PERSISTENT_STORAGE = FeatureFlagField(label=_("开启持久存储挂载卷"), default=False)


class LightApplicationViewSetErrorCode(StrStructuredEnum):
    SUCCESS = "0"
    PARAM_NOT_VALID = "1301100"
    CREATE_APP_ERROR = "1301101"
    EDIT_APP_ERROR = "1301102"
    ESB_NOT_VALID = "1301103"
    APP_NOT_EXIST = "1301104"
    NO_PERMISSION = "1301105"


class AvailabilityLevel(StrStructuredEnum):
    STANDARD = EnumField("standard", label="基础")
    PREMIUM = EnumField("premium", label="高级别")
