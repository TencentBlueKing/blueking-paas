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

"""Serializer for third-party api"""
from rest_framework import serializers

from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.serializers import AppIDField, AppNameField
from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n
from paasng.utils.serializers import field_env_var_key


class PluginTemplateSLZ(serializers.Serializer):
    """插件模板相关字段"""

    id = serializers.CharField()
    name = serializers.CharField()
    language = serializers.CharField()
    applicable_language = serializers.CharField(allow_null=True)
    repository = serializers.CharField()


@i18n
class PluginSyncRequestSLZ(serializers.Serializer):
    """同步插件信息至第三方系统的请求体格式"""

    id = AppIDField()
    name = I18NExtend(AppNameField())
    template = PluginTemplateSLZ()
    extra_fields = serializers.DictField(allow_null=True, help_text="第三方系统声明的额外字段")
    repository = serializers.CharField(help_text="源码仓库")
    operator = serializers.CharField()


class PluginArchiveRequestSLZ(serializers.Serializer):
    """下架插件的请求体格式"""

    operator = serializers.CharField()


class PluginMarketRequestSLZ(serializers.Serializer):
    """同步插件市场信息至第三方系统的请求体格式"""

    category = serializers.CharField(allow_null=True)
    introduction = TranslatedCharField(allow_null=True)
    contact = serializers.CharField(allow_null=True, help_text="以分号(;)分割")
    extra_fields = serializers.DictField(allow_null=True, help_text="第三方系统声明的额外字段")
    operator = serializers.CharField()


class MarketCategorySLZ(serializers.Serializer):
    """插件市场-插件类别"""

    name = serializers.CharField()
    value = serializers.CharField()


class PluginReleaseVersionSLZ(serializers.Serializer):
    """插件发布版本的结构"""

    type = serializers.CharField(help_text="版本类型(正式/测试)")
    version = serializers.CharField(help_text="版本号")
    comment = serializers.CharField(help_text="版本日志")
    extra_fields = serializers.DictField(help_text="额外字段", default=dict)
    semver_type = serializers.CharField(help_text="语义化版本类型(相对于上一个版本而言)", allow_null=True)

    source_location = serializers.CharField(help_text="代码仓库地址")
    source_version_type = serializers.CharField(help_text="代码版本类型(branch/tag)")
    source_version_name = serializers.CharField(help_text="代码分支名/tag名")
    source_hash = serializers.CharField(help_text="代码提交哈希")


class DeployPluginRequestSLZ(serializers.Serializer):
    """插件部署操作的请求体格式"""

    plugin_id = serializers.CharField(help_text="插件id")
    version = PluginReleaseVersionSLZ(help_text="插件发布版本信息")
    operator = serializers.CharField(help_text="操作人")


class DeployStepSLZ(serializers.Serializer):
    """部署步骤的结构"""

    id = serializers.CharField(help_text="部署步骤id", source="name")
    name = serializers.CharField(help_text="部署步骤名称", source="display_name")
    start_time = serializers.DateTimeField(help_text="开始时间", allow_null=True)
    complete_time = serializers.DateTimeField(help_text="结束时间", allow_null=True)
    status = serializers.CharField(help_text="执行状态", allow_null=True)


class PluginDeployResponseSLZ(serializers.Serializer):
    """插件部署操作/检测部署状态的返回体格式"""

    deploy_id = serializers.CharField(help_text="部署操作id")
    status = serializers.CharField(allow_null=True, allow_blank=True)
    detail = serializers.CharField(allow_null=True, help_text="状态的具体信息")
    steps = DeployStepSLZ(many=True)


class PluginReleaseLogsResponseSLZ(serializers.Serializer):
    """插件发布日志的返回体格式"""

    finished = serializers.BooleanField(help_text="日志是否结束", default=False)
    logs = serializers.ListSerializer(
        child=serializers.CharField(help_text="日志内容", allow_null=True, allow_blank=True)
    )


class PluginRoleSLZ(serializers.Serializer):
    name = serializers.CharField(read_only=True, help_text="角色名称")
    # NOTE: 目前插件开发中心的角色ID与开发者中心的角色ID一致
    id = serializers.ChoiceField(help_text="角色ID", choices=ApplicationRole.get_choices())


class PluginMemberSLZ(serializers.Serializer):
    username = serializers.CharField(help_text="用户名")
    role = PluginRoleSLZ(help_text="角色")


class PluginConfigSLZ(serializers.Serializer):
    """插件配置-环境变量的结构"""

    key = field_env_var_key()
    value = serializers.CharField(help_text="环境变量值", required=True, allow_blank=True)
    description = serializers.CharField(
        allow_blank=True, max_length=200, required=False, default="", help_text="变量描述，不超过 200 个字符"
    )
