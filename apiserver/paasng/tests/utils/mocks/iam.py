# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
import logging
from typing import Dict, List

from bkpaas_auth import get_user_by_user_id

from paasng.accessories.iam.constants import APP_DEFAULT_ROLES
from paasng.accessories.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.constants import ApplicationRole
from tests.utils.auth import create_user

logger = logging.getLogger(__name__)


class StubBKIAMClient:
    """bk-iam 通过 APIGW 提供的 API（仅供单元测试使用）"""

    def create_grade_managers(self, app_code: str, app_name: str, creator: str) -> int:
        """创建分级管理员"""
        latest_manager = ApplicationGradeManager.objects.all().last()
        grade_manager_id = latest_manager.id + 1 if latest_manager else 1
        return grade_manager_id

    def fetch_grade_manager_members(self, grade_manager_id: int) -> List[str]:
        """获取分级管理员 -> 返回管理者列表（从 ApplicationMembership 表获取）"""
        from paasng.platform.applications.models import ApplicationMembership

        app = self._get_app_by_grade_manager_id(grade_manager_id)
        return [
            get_user_by_user_id(ship.user, username_only=True).username
            for ship in ApplicationMembership.objects.filter(application=app, role=ApplicationRole.ADMINISTRATOR)
        ]

    def add_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """向某个分级管理员添加成员 -> 管理 ApplicationMembership 表"""
        from paasng.platform.applications.models import ApplicationMembership

        app = self._get_app_by_grade_manager_id(grade_manager_id)
        for username in usernames:
            new_user = create_user(username)
            if ApplicationMembership.objects.filter(
                application=app, role=ApplicationRole.ADMINISTRATOR, user=new_user
            ).exists():
                continue

            ApplicationMembership.objects.create(application=app, role=ApplicationRole.ADMINISTRATOR, user=new_user)

    def delete_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """删除某个分级管理员的成员 -> 从 ApplicationMembership 表中找出来，删除掉"""
        from paasng.platform.applications.models import ApplicationMembership

        app = self._get_app_by_grade_manager_id(grade_manager_id)
        for ms in ApplicationMembership.objects.filter(application=app, role=ApplicationRole.ADMINISTRATOR):
            if get_user_by_user_id(ms.user, username_only=True).username in usernames:
                ms.delete()

    def create_builtin_user_groups(self, grade_manager_id: int, app_code: str) -> List[Dict]:
        """为单个应用创建用户组（默认3个：管理员，开发者，运营者）"""
        latest_user_group = ApplicationUserGroup.objects.all().last()
        user_group_id_start_at = latest_user_group.id + 1 if latest_user_group else 1

        return [
            {'id': user_group_id_start_at + idx, 'role': role, 'name': f'{role.name} user group', 'readonly': True}
            for idx, role in enumerate(APP_DEFAULT_ROLES)
        ]

    def delete_user_groups(self, user_group_ids: List[int]):
        """删除应用的默认用户组（管理员，开发者，运营者）"""

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        """获取某个用户组成员信息"""
        from paasng.platform.applications.models import ApplicationMembership

        user_group, app = self._get_group_and_app_by_user_group_id(user_group_id)
        return [
            get_user_by_user_id(ms.user, username_only=True).username
            for ms in ApplicationMembership.objects.filter(application=app, role=user_group.role)
        ]

    def add_user_group_members(self, user_group_id: int, usernames: List[str], expired_after_days: int):
        """向某个用户组添加成员"""
        from paasng.platform.applications.models import ApplicationMembership

        user_group, app = self._get_group_and_app_by_user_group_id(user_group_id)
        for username in usernames:
            new_user = create_user(username)
            if ApplicationMembership.objects.filter(application=app, role=user_group.role, user=new_user).exists():
                continue

            ApplicationMembership.objects.create(application=app, role=user_group.role, user=new_user)

    def delete_user_group_members(self, user_group_id: int, usernames: List[str]):
        """删除某个用户组的成员"""
        from paasng.platform.applications.models import ApplicationMembership

        user_group, app = self._get_group_and_app_by_user_group_id(user_group_id)
        for ms in ApplicationMembership.objects.filter(application=app, role=user_group.role):
            if get_user_by_user_id(ms.user, username_only=True).username in usernames:
                ms.delete()

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[Dict]):
        """为默认的用户组授权"""

    @staticmethod
    def _get_app_by_grade_manager_id(grade_manager_id: int):
        from paasng.platform.applications.models import Application

        return Application.objects.get(
            code=ApplicationGradeManager.objects.get(grade_manager_id=grade_manager_id).app_code
        )

    @staticmethod
    def _get_group_and_app_by_user_group_id(user_group_id: int):
        from paasng.platform.applications.models import Application

        user_group = ApplicationUserGroup.objects.get(user_group_id=user_group_id)
        app = Application.objects.get(code=user_group.app_code)
        return user_group, app
