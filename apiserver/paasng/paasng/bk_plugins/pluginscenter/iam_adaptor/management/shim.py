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

# IAM management API shim
import functools
from operator import attrgetter
from typing import List, Optional

import cattr
from attrs import define
from blue_krill.web.std_error import APIError
from django.conf import settings

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.iam_adaptor import definitions
from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import NEVER_EXPIRE_DAYS, PLUGIN_BUILTIN_ROLES
from paasng.bk_plugins.pluginscenter.iam_adaptor.management.client import lazy_iam_client
from paasng.bk_plugins.pluginscenter.iam_adaptor.models import PluginGradeManager, PluginUserGroup
from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.infras.iam.exceptions import BKIAMApiError, BKIAMGatewayServiceError


@define
class Role:
    id: PluginRole
    name: str


@define
class PluginMember:
    username: str
    role: Role


def transform_api_error(func):
    """a decorator transform IAM client exception to APIError"""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BKIAMApiError as e:
            raise APIError("BKIAMApiError", e.message, e.code or -1) from e
        except BKIAMGatewayServiceError as e:
            raise APIError("BKIAMGatewayServiceError", e.message) from e

    return wrapped


@transform_api_error
def fetch_grade_manager_members(plugin: PluginInstance) -> List[str]:
    """获取指定插件的分级管理员名单

    :param plugin: 蓝鲸插件
    """
    iam_grade_manager = PluginGradeManager.objects.filter_by_plugin(plugin).get()
    return lazy_iam_client.fetch_grade_manager_members(iam_grade_manager.grade_manager_id)


@transform_api_error
def fetch_role_members(plugin: PluginInstance, role: PluginRole) -> List[str]:
    """获取指定插件属于指定角色的用户列表

    :param plugin: 蓝鲸插件
    :param role: 插件角色
    """
    iam_group = PluginUserGroup.objects.filter_by_plugin(plugin).get(role=role)
    return lazy_iam_client.fetch_user_group_members(iam_group.user_group_id)


@transform_api_error
def add_role_members(
    plugin: PluginInstance, role: PluginRole, usernames: List[str], expired_after_days: int = NEVER_EXPIRE_DAYS
):
    """将用户添加为某个角色的成员

    :param plugin: 蓝鲸插件
    :param role: 插件角色
    :param usernames: 待添加成员名称列表
    :param expired_after_days: X 天后权限过期（-1 表示永不过期）
    """
    # 如果是管理者，还要添加成分级管理员
    if role == PluginRole.ADMINISTRATOR:
        iam_grade_manager = PluginGradeManager.objects.filter_by_plugin(plugin).get()
        lazy_iam_client.add_grade_manager_members(
            grade_manager_id=iam_grade_manager.grade_manager_id,
            usernames=usernames,
        )

    iam_group = PluginUserGroup.objects.filter_by_plugin(plugin).get(role=role)
    lazy_iam_client.add_user_group_members(
        user_group_id=iam_group.user_group_id,
        usernames=usernames,
        expired_after_days=expired_after_days,
    )


@transform_api_error
def delete_role_members(plugin: PluginInstance, role: PluginRole, usernames: List[str]):
    """将用户从某个角色的成员中删除

    :param plugin: 蓝鲸插件
    :param role: 插件角色
    :param usernames: 待删除的成员名称列表
    """
    # 如果是管理者，还要从分级管理员中移除
    if role == PluginRole.ADMINISTRATOR:
        iam_grade_manager = PluginGradeManager.objects.filter_by_plugin(plugin).get()
        lazy_iam_client.delete_grade_manager_members(
            grade_manager_id=iam_grade_manager.grade_manager_id,
            usernames=usernames,
        )

    iam_group = PluginUserGroup.objects.filter_by_plugin(plugin).get(role=role)
    return lazy_iam_client.delete_user_group_members(
        user_group_id=iam_group.user_group_id,
        usernames=usernames,
    )


@transform_api_error
def fetch_user_roles(plugin: PluginInstance, username: str) -> List[PluginRole]:
    """获取用户在插件中的对应的角色"""
    user_roles = []
    for group in PluginUserGroup.objects.filter_by_plugin(plugin):
        if username in lazy_iam_client.fetch_user_group_members(group.user_group_id):
            user_roles.append(PluginRole(group.role))

    return sorted(user_roles)


def fetch_user_main_role(plugin: PluginInstance, username: str) -> Optional[Role]:
    """获取用户在插件中的主要角色"""
    roles = fetch_user_roles(plugin, username)
    if len(roles) > 0:
        role = roles[0]
        return cattr.structure({"id": PluginRole(role), "name": PluginRole.get_choice_label(role)}, Role)
    return None


@transform_api_error
def remove_user_all_roles(plugin: PluginInstance, usernames: List[str]):
    """
    删除用户在某个 APP 下的所有权限角色

    :param plugin: 蓝鲸插件
    :param usernames: 待删除的成员名称列表
    """
    if not usernames:
        return

    # 先清理掉分级管理员权限
    iam_grade_manager = PluginGradeManager.objects.filter_by_plugin(plugin).get()
    lazy_iam_client.delete_grade_manager_members(
        grade_manager_id=iam_grade_manager.grade_manager_id,
        usernames=usernames,
    )

    # 再将所有的内建角色权限清理掉
    role_group_id_map = {group.role: group.user_group_id for group in PluginUserGroup.objects.filter_by_plugin(plugin)}
    for group_id in role_group_id_map.values():
        lazy_iam_client.delete_user_group_members(group_id, usernames)


@transform_api_error
def fetch_plugin_members(plugin: PluginInstance) -> List[PluginMember]:
    """
    获取一个蓝鲸插件所有用户（包含角色信息）
    顺序：管理员(role=2) - 开发者(role=3)

    :param plugin: 蓝鲸插件
    """
    members = []
    for group in PluginUserGroup.objects.filter_by_plugin(plugin):
        members.extend(
            [
                {
                    "role": {"id": PluginRole(group.role), "name": PluginRole.get_choice_label(group.role)},
                    "username": username,
                }
                for username in lazy_iam_client.fetch_user_group_members(group.user_group_id)
            ]
        )
    return sorted(cattr.structure(members, List[PluginMember]), key=attrgetter("role.id"))


@transform_api_error
def setup_builtin_grade_manager(plugin: PluginInstance):
    """初始化插件的分级管理员

    :param plugin: 蓝鲸插件
    """
    if PluginGradeManager.objects.filter_by_plugin(plugin).exists():
        return PluginGradeManager.objects.filter_by_plugin(plugin).get()
    grade_manager_id = lazy_iam_client.create_grade_manager(
        plugin_resource=definitions.gen_iam_resource(plugin),
        manager_definition=definitions.gen_iam_grade_manager(plugin),
    )
    return PluginGradeManager.objects.create(
        pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=grade_manager_id
    )


@transform_api_error
def setup_builtin_user_groups(plugin: PluginInstance):
    """初始化插件的内建用户组

    :param plugin: 蓝鲸插件
    """
    grade_manager_id = PluginGradeManager.objects.filter_by_plugin(plugin).get().grade_manager_id
    missing_groups = []
    for role in PLUGIN_BUILTIN_ROLES:
        if PluginUserGroup.objects.filter_by_plugin(plugin).filter(role=role).exists():
            continue
        missing_groups.append(definitions.gen_plugin_user_group(plugin=plugin, role=role))

    created_groups = lazy_iam_client.create_user_groups(grade_manager_id=grade_manager_id, groups=missing_groups)
    lazy_iam_client.initial_user_group_policies(
        plugin_resource=definitions.gen_iam_resource(plugin), groups=created_groups
    )
    for group in created_groups:
        PluginUserGroup.objects.create(
            pd_id=plugin.pd.identifier,
            plugin_id=plugin.id,
            role=group.role,
            user_group_id=group.id,
        )


def delete_builtin_user_groups(plugin: PluginInstance):
    """删除插件的内建用户组

    :param plugin: 蓝鲸插件
    """
    user_groups = PluginUserGroup.objects.filter_by_plugin(plugin)
    lazy_iam_client.delete_user_groups(user_groups.values_list("user_group_id", flat=True))
    user_groups.delete()


def user_group_apply_url(plugin_id: str) -> dict:
    """应用用户组权限申请链接"""
    dev_user_group_id = PluginUserGroup.objects.get(plugin_id=plugin_id, role=PluginRole.DEVELOPER).user_group_id
    return {
        "apply_url_for_dev": settings.BK_IAM_USER_GROUP_APPLY_TMPL.format(user_group_id=dev_user_group_id),
    }
