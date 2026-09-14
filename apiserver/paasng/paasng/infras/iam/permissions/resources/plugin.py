# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from typing import List

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class PluginPermissionActions(StrStructuredEnum):
    """插件相关的操作权限"""

    BASIC_DEVELOPMENT = EnumField("basic_development", label=_("基础开发"))
    RELEASE_VERSION = EnumField("release_version", label=_("版本发布"))
    EDIT_PLUGIN = EnumField("edit_plugin", label=_("编辑插件信息"))
    MANAGE_VISIBILITY = EnumField("manage_visibility", label=_("可见范围管理"))
    MANAGE_CONFIGURATION = EnumField("manage_configuration", label=_("插件配置管理"))
    MANAGE_MEMBERS = EnumField("manage_members", label=_("成员管理"))
    DELETE_PLUGIN = EnumField("delete_plugin", label=_("删除插件"))


class PluginIAMRole(StrStructuredEnum):
    """插件在 IAM V4 上注册的角色

    与 `PluginRole`（数值 2/3，前端契约）不同：本枚举的值是提交给权限中心的字符串 ID。
    """

    ADMINISTRATOR = EnumField("plugin_administrator", label=_("插件管理员"))
    DEVELOPER = EnumField("plugin_developer", label=_("插件开发者"))

    @classmethod
    def get_description(cls, role: "PluginIAMRole") -> str:
        return {
            cls.ADMINISTRATOR: "插件负责人，可管理成员、删除插件、配置全部能力",
            cls.DEVELOPER: "负责插件开发与版本发布",
        }[role]

    @classmethod
    def get_actions(cls, role: "PluginIAMRole") -> List[PluginPermissionActions]:
        """角色对应的操作清单，以 V3 授权路径历史生效定义为准。

        开发者 5 项（含 edit_plugin、manage_visibility），不用界面预设模板中的较小集合。
        """
        return {
            cls.ADMINISTRATOR: [
                PluginPermissionActions.BASIC_DEVELOPMENT,
                PluginPermissionActions.RELEASE_VERSION,
                PluginPermissionActions.EDIT_PLUGIN,
                PluginPermissionActions.DELETE_PLUGIN,
                PluginPermissionActions.MANAGE_MEMBERS,
                PluginPermissionActions.MANAGE_VISIBILITY,
                PluginPermissionActions.MANAGE_CONFIGURATION,
            ],
            cls.DEVELOPER: [
                PluginPermissionActions.BASIC_DEVELOPMENT,
                PluginPermissionActions.RELEASE_VERSION,
                PluginPermissionActions.MANAGE_CONFIGURATION,
                PluginPermissionActions.EDIT_PLUGIN,
                PluginPermissionActions.MANAGE_VISIBILITY,
            ],
        }[role]
