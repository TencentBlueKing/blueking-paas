# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import List

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

from paasng.bk_plugins.pluginscenter.constants import PluginRole

# 永不过期的时间（伪，其实是 2100.01.01 08:00:00，与权限中心保持一致)
NEVER_EXPIRE_TIMESTAMP = 4102444800

# 每一天的秒数
ONE_DAY_SECONDS = 24 * 60 * 60

# 默认为每个 APP 创建 2 个用户组，分别是管理者，开发者
PLUGIN_BUILTIN_ROLES = [PluginRole.ADMINISTRATOR, PluginRole.DEVELOPER]

# 默认从第一页查询
DEFAULT_PAGE = 1

# 查询用户组成员，全量查询
FETCH_USER_GROUP_MEMBERS_LIMIT = 10000

# 永不过期
NEVER_EXPIRE_DAYS = -1


class PluginPermissionActions(str, StructuredEnum):
    """插件相关的操作权限"""

    BASIC_DEVELOPMENT = EnumField("basic_development", label=_("基础开发"))
    RELEASE_VERSION = EnumField("release_version", label=_("版本发布"))
    EDIT_PLUGIN = EnumField("edit_plugin", label=_("编辑插件信息"))
    DELETE_PLUGIN = EnumField("delete_plugin", label=_("删除插件"))
    MANAGE_MEMBERS = EnumField("manage_members", label=_("成员管理"))
    MANAGE_VISIBILITY = EnumField("manage_visibility", label=_("可见范围管理"))
    MANAGE_CONFIGURATION = EnumField("manage_configuration", label=_("插件配置管理"))

    @classmethod
    def get_choices_by_role(cls, role: PluginRole) -> List['PluginPermissionActions']:
        if role == PluginRole.ADMINISTRATOR:
            return [
                PluginPermissionActions.BASIC_DEVELOPMENT,
                PluginPermissionActions.RELEASE_VERSION,
                PluginPermissionActions.EDIT_PLUGIN,
                PluginPermissionActions.DELETE_PLUGIN,
                PluginPermissionActions.MANAGE_MEMBERS,
                PluginPermissionActions.MANAGE_VISIBILITY,
                PluginPermissionActions.MANAGE_CONFIGURATION,
            ]
        elif role == PluginRole.DEVELOPER:
            return [
                PluginPermissionActions.BASIC_DEVELOPMENT,
                PluginPermissionActions.RELEASE_VERSION,
                PluginPermissionActions.MANAGE_CONFIGURATION,
            ]
        raise NotImplementedError


class ResourceType(str, StructuredEnum):
    PLUGIN = EnumField("plugin", label=_("蓝鲸插件"))
