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

from typing import Dict, List, Union

from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings

from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.tenant import get_tenant_id_for_app

from .client import BKIAMClient
from .constants import APP_DEFAULT_ROLES, NEVER_EXPIRE_DAYS


def fetch_role_members(app_code: str, role: ApplicationRole) -> List[str]:
    """
    通过指定应用与角色，获取对应的用户组信息

    :param app_code: 蓝鲸应用 ID
    :param role: 应用角色
    """
    tenant_id = get_tenant_id_for_app(app_code)
    return BKIAMClient(tenant_id).fetch_user_group_members(
        user_group_id=ApplicationUserGroup.objects.get(app_code=app_code, role=role).user_group_id
    )


def add_role_members(
    app_code: str, role: ApplicationRole, usernames: Union[List[str], str], expired_after_days: int = NEVER_EXPIRE_DAYS
):
    """
    将用户添加为某个角色的成员

    :param app_code: 蓝鲸应用 ID
    :param role: 应用角色
    :param usernames: 待添加成员名称，支持单个或多个
    :param expired_after_days: X 天后权限过期（-1 表示永不过期）
    """
    usernames = [usernames] if isinstance(usernames, str) else usernames

    tenant_id = get_tenant_id_for_app(app_code)
    iam_client = BKIAMClient(tenant_id)
    # 如果是管理者，还要添加成分级管理员
    if role == ApplicationRole.ADMINISTRATOR:
        iam_client.add_grade_manager_members(
            grade_manager_id=ApplicationGradeManager.objects.get(app_code=app_code).grade_manager_id,
            usernames=usernames,
        )

    return iam_client.add_user_group_members(
        user_group_id=ApplicationUserGroup.objects.get(app_code=app_code, role=role).user_group_id,
        usernames=usernames,
        expired_after_days=expired_after_days,
    )


def delete_role_members(app_code: str, role: ApplicationRole, usernames: Union[List[str], str]):
    """
    将用户从某个角色的成员中删除

    :param app_code: 蓝鲸应用 ID
    :param role: 应用角色
    :param usernames: 待添加成员名称，支持单个或多个
    """
    usernames = [usernames] if isinstance(usernames, str) else usernames
    tenant_id = get_tenant_id_for_app(app_code)
    iam_client = BKIAMClient(tenant_id)
    # 如果是管理者，还要从分级管理员中移除
    if role == ApplicationRole.ADMINISTRATOR:
        iam_client.delete_grade_manager_members(
            grade_manager_id=ApplicationGradeManager.objects.get(app_code=app_code).grade_manager_id,
            usernames=usernames,
        )

    return iam_client.delete_user_group_members(
        user_group_id=ApplicationUserGroup.objects.get(app_code=app_code, role=role).user_group_id,
        usernames=usernames,
    )


def fetch_user_roles(app_code: str, username: str) -> List[ApplicationRole]:
    """原实现中用户只会有一个角色，但是接入权限中心后，角色表现为用户组，同一用户可能有多个角色"""
    if username == settings.ADMIN_USERNAME:
        return [ApplicationRole.ADMINISTRATOR]

    user_roles = []
    tenant_id = get_tenant_id_for_app(app_code)
    iam_client = BKIAMClient(tenant_id)
    for group in ApplicationUserGroup.objects.filter(app_code=app_code).order_by("role"):
        if username in iam_client.fetch_user_group_members(group.user_group_id):
            user_roles.append(ApplicationRole(group.role))

    if not user_roles:
        return [ApplicationRole.NOBODY]

    return user_roles


def fetch_user_main_role(app_code: str, username: str) -> ApplicationRole:
    """获取用户在某个应用中最高优先级的角色"""
    if username == settings.ADMIN_USERNAME:
        return ApplicationRole.ADMINISTRATOR

    tenant_id = get_tenant_id_for_app(app_code)
    iam_client = BKIAMClient(tenant_id)
    for group in ApplicationUserGroup.objects.filter(app_code=app_code).order_by("role"):
        if username in iam_client.fetch_user_group_members(group.user_group_id):
            return ApplicationRole(group.role)

    return ApplicationRole.NOBODY


def remove_user_all_roles(app_code: str, usernames: Union[List[str], str]):
    """
    删除用户在某个 APP 下的所有权限角色

    :param app_code: 蓝鲸应用 ID
    :param usernames: 待添加成员名称，支持单个或多个
    """
    usernames = [usernames] if isinstance(usernames, str) else usernames

    if not usernames:
        return

    tenant_id = get_tenant_id_for_app(app_code)
    iam_client = BKIAMClient(tenant_id)

    # 先清理掉分级管理员权限
    iam_client.delete_grade_manager_members(
        grade_manager_id=ApplicationGradeManager.objects.get(app_code=app_code).grade_manager_id,
        usernames=usernames,
    )

    role_group_id_map = {
        group.role: group.user_group_id for group in ApplicationUserGroup.objects.filter(app_code=app_code)
    }
    # 再将所有的内建角色权限清理掉
    for role in APP_DEFAULT_ROLES:
        iam_client.delete_user_group_members(role_group_id_map[role], usernames)


def fetch_application_members(app_code: str) -> List[Dict]:
    """
    获取一个蓝鲸应用所有用户（包含角色信息）
    顺序：管理员 - 开发者 - 运营者
    """
    tenant_id = get_tenant_id_for_app(app_code)
    iam_client = BKIAMClient(tenant_id)

    member_map: Dict[str, Dict] = {}
    for group in ApplicationUserGroup.objects.filter(app_code=app_code).order_by("role"):
        for username in iam_client.fetch_user_group_members(group.user_group_id):
            if username not in member_map:
                member_map[username] = {
                    "roles": [group.role],
                    "username": username,
                    "user": user_id_encoder.encode(username=username, provider_type=settings.USER_TYPE),
                }
            else:
                member_map[username]["roles"].append(group.role)

    return list(member_map.values())


def delete_builtin_user_groups(app_code: str):
    """删除应用的内建用户组"""
    user_groups = ApplicationUserGroup.objects.filter(app_code=app_code)
    tenant_id = get_tenant_id_for_app(app_code)
    BKIAMClient(tenant_id).delete_user_groups(user_groups.values_list("user_group_id", flat=True))
    user_groups.delete()


def delete_grade_manager(app_code: str):
    """删除应用的分级管理员"""
    grade_manager = ApplicationGradeManager.objects.filter(app_code=app_code).first()
    if not grade_manager:
        return

    tenant_id = get_tenant_id_for_app(app_code)
    BKIAMClient(tenant_id).delete_grade_manager(grade_manager.grade_manager_id)
    grade_manager.delete()


def user_group_apply_url(app_code: str) -> dict:
    """应用用户组权限申请链接"""
    ops_user_group_id = ApplicationUserGroup.objects.get(
        app_code=app_code, role=ApplicationRole.OPERATOR
    ).user_group_id
    dev_user_group_id = ApplicationUserGroup.objects.get(
        app_code=app_code, role=ApplicationRole.DEVELOPER
    ).user_group_id
    return {
        "apply_url_for_ops": settings.BK_IAM_USER_GROUP_APPLY_TMPL.format(user_group_id=ops_user_group_id),
        "apply_url_for_dev": settings.BK_IAM_USER_GROUP_APPLY_TMPL.format(user_group_id=dev_user_group_id),
    }
