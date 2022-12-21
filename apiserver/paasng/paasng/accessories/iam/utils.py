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
import time
from typing import List

from django.utils.translation import gettext as _

from paasng.platform.applications.constants import ApplicationRole

from .constants import NEVER_EXPIRE_TIMESTAMP, ONE_DAY_SECONDS
from .permissions.resources.application import AppAction


def gen_grade_manager_name(app_code: str) -> str:
    """
    生成分级管理员名称（最大字符数限制 32）
    中：开发者中心-{app_code}
    英：PaaS-{app_code}
    """
    return _('开发者中心-{}').format(app_code)


def gen_grade_manager_desc(app_code: str) -> str:
    """
    生成分级管理员描述
    中：开发者中心应用（{app_code}）分级管理员，拥有审批用户加入管理者/开发者/运营者用户组权限。
    英：Developer center application ({app_code}) grade administrator,
        with permission to approve users to join the administrator/developer/operator user group.
    """
    return _('开发者中心应用（{}）分级管理员，拥有审批用户加入管理者/开发者/运营者用户组权限。').format(app_code)


def gen_user_group_name(app_code: str, role: ApplicationRole) -> str:
    """
    根据指定的用户角色，生成对应的用户组名称（最大字符数限制 32）
    中：开发者中心-{app_code}-管理员 ｜ 开发者中心-{app_code}-开发者 ｜ 开发者中心-{app_code}-运营者
    英：PaaS-{app_code}-admin | PaaS-{app_code}-dev | PaaS-{app_code}-ops
    """
    if role == ApplicationRole.ADMINISTRATOR:
        return _('开发者中心-{}-管理员').format(app_code)
    elif role == ApplicationRole.DEVELOPER:
        return _('开发者中心-{}-开发者').format(app_code)
    elif role == ApplicationRole.OPERATOR:
        return _('开发者中心-{}-运营者').format(app_code)
    return ''


def gen_user_group_desc(app_code: str, role: ApplicationRole) -> str:
    """
    根据指定的用户角色，生成对应的用户组名称
    中：开发者中心应用（{app_code}）管理员，拥有应用的全部权限。
        开发者中心应用（{app_code}）开发者，拥有应用的开发权限，如基础开发，云 API 管理等。
        开发者中心应用（{app_code}）运营者，拥有应用的运营权限，如基础信息编辑，访问控制管理，应用市场管理等。
    英：The developer center application ({app_code}) administrator, has all the permissions of the application.
        The developer center application ({app_code}) developer, with application development permissions,
            such as basic development, cloud API management, etc.
        The developer center application ({app_code}) operator, with application operation permissions,
            such as basic information editing, access control management, application market management, etc.
    """
    if role == ApplicationRole.ADMINISTRATOR:
        return _('开发者中心应用（{}）管理员，拥有应用的全部权限。').format(app_code)
    elif role == ApplicationRole.DEVELOPER:
        return _('开发者中心应用（{}）开发者，拥有应用的开发权限，如基础开发，云 API 管理等。').format(app_code)
    elif role == ApplicationRole.OPERATOR:
        return _('开发者中心应用（{}）运营者，拥有应用的运营权限，如基础信息编辑，访问控制管理，应用市场管理等。').format(app_code)
    return ''


def calc_expired_at(expire_after_days: int) -> int:
    """计算过期的时间戳，若传入的过期天数为负数，则表示永不过期"""
    if expire_after_days < 0:
        return NEVER_EXPIRE_TIMESTAMP

    return int(time.time()) + expire_after_days * ONE_DAY_SECONDS


def get_app_actions_by_role(role: ApplicationRole) -> List[AppAction]:
    """根据角色类型，获取他们拥有的 APP 权限"""
    # 管理者
    if role == ApplicationRole.ADMINISTRATOR:
        return [action for action in AppAction.get_values()]
    # 开发者
    elif role == ApplicationRole.DEVELOPER:
        return [
            AppAction.VIEW_BASIC_INFO,
            AppAction.MANAGE_APP_MARKET,
            AppAction.DATA_STATISTICS,
            AppAction.BASIC_DEVELOP,
            AppAction.MANAGE_CLOUD_API,
            AppAction.VIEW_ALERT_RECORDS,
            AppAction.EDIT_ALERT_POLICY,
        ]
    # 运营者
    elif role == ApplicationRole.OPERATOR:
        return [
            AppAction.VIEW_BASIC_INFO,
            AppAction.EDIT_BASIC_INFO,
            AppAction.MANAGE_ACCESS_CONTROL,
            AppAction.MANAGE_APP_MARKET,
            AppAction.DATA_STATISTICS,
            AppAction.VIEW_ALERT_RECORDS,
        ]

    return []
