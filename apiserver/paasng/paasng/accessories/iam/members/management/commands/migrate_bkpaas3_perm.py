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
import time
from collections import defaultdict
from typing import List

from django.core.management.base import BaseCommand

from paasng.accessories.iam.client import BKIAMClient
from paasng.accessories.iam.constants import NEVER_EXPIRE_DAYS
from paasng.accessories.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, ApplicationMembership
from paasng.utils.basic import get_username_by_bkpaas_user_id

# 打印应用 ID 信息时，每行展示数量
PRE_LINE_LIMIT = 15

# APP 权限数据迁移间隔
MIGRATE_APP_INTERVAL = 0.05


class Command(BaseCommand):
    """
    蓝鲸应用成员关系迁移到权限中心命令行工具
    # TODO 支持 --exclude 以跳过某些不需要迁移的应用

    使用示例：
    python manage.py migrate_bkpaas3_perm                             # 迁移全量数据
    python manage.py migrate_bkpaas3_perm --dry-run                   # 仅打印待的权限数据信息
    python manage.py migrate_bkpaas3_perm --apps app_code1 app_code2  # 迁移指定的应用权限数据
    """

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', help='dry run only', action='store_true')
        parser.add_argument('--apps', nargs='*', help='specified app code list')
        parser.set_defaults(is_enabled=True)

    def handle(self, dry_run, apps, *args, **options):
        self.dry_run: bool = dry_run
        self.apps: List[str] = apps
        self.cli = BKIAMClient()

        self._prepare()
        self._migrate()

    def _prepare(self):
        """中间态数据准备"""
        print('------------------ start data preparation -----------------')

        applications = Application.objects.filter(is_deleted=False)
        grade_managers = ApplicationGradeManager.objects.all()
        user_groups = ApplicationUserGroup.objects.all()
        memberships = ApplicationMembership.objects.select_related('application').all()

        if self.apps:
            applications = applications.filter(code__in=self.apps)
            grade_managers = grade_managers.filter(app_code__in=self.apps)
            user_groups = user_groups.filter(app_code__in=self.apps)
            memberships = memberships.filter(application__code__in=self.apps)

        # 待迁移应用数据
        self.applications = [
            {
                'id': app.id,
                'code': app.code,
                'name': app.code,
                'creator': get_username_by_bkpaas_user_id(app.creator),
            }
            for app in applications
        ]
        # 应用 => 分级管理员 ID
        self.grade_manager_map = {m.app_code: m.grade_manager_id for m in grade_managers}
        # 应用 + 身份 => 用户组 ID
        self.user_group_map = {(g.app_code, g.role): g.user_group_id for g in user_groups}
        # 应用 + 身份 => 成员列表
        self.members_map = defaultdict(list)
        for m in memberships:
            self.members_map[(m.application.code, m.role)].append(get_username_by_bkpaas_user_id(m.user))

        self.total_count = len(self.applications)

        print(f'{self.total_count} applications waiting for migrate:')

        for start_at in range(0, self.total_count, PRE_LINE_LIMIT):
            end_at = start_at + PRE_LINE_LIMIT
            end_at = end_at if end_at < self.total_count else self.total_count
            print(
                f'{start_at+1} - {end_at}:'.rjust(11),
                ' '.join([app['code'] for app in self.applications[start_at:end_at]]),
            )

        print('---------------- data preparation finished ----------------')

    def _migrate(self):
        """迁移权限数据"""
        if self.dry_run:
            print('------------------------- DRY-RUN -------------------------')
            return

        print('---------------- start migrate applications role data ----------------')

        for idx, app in enumerate(self.applications, start=1):
            app_code, app_name, creator = app['code'], app['name'], app['creator']

            administrator_key = (app_code, ApplicationRole.ADMINISTRATOR)
            developer_key = (app_code, ApplicationRole.DEVELOPER)
            operator_key = (app_code, ApplicationRole.OPERATOR)
            all_role_keys = [administrator_key, developer_key, operator_key]

            print(f'start migrate application [{app_name}/{app_code}] user roles... {idx}/{self.total_count}')

            # 1。检查有没有该应用的分级管理员信息，如果没有，则需要创建
            grade_manager_id = self.grade_manager_map.get(app_code)
            if not grade_manager_id:
                print(f"grade manager not exists, create and add app's creator [{creator}] as members...\n")
                grade_manager_id = self.cli.create_grade_managers(app_code, app_name, creator)

                # 更新分级管理员映射表信息 & ApplicationGradeManager 表数据
                self.grade_manager_map[app_code] = grade_manager_id
                ApplicationGradeManager.objects.create(app_code=app_code, grade_manager_id=grade_manager_id)

            # 2. 获取具有管理员身份的用户名，如果没有，则默认将创建者添加为分级管理员（拥有审批加入用户组权限）
            administrators = self.members_map[administrator_key] or [creator]
            self.cli.add_grade_manager_members(grade_manager_id, administrators)
            print(
                f'add grade manager (id: {grade_manager_id}) members:\n'
                f'count: {len(administrators)}, users: {administrators}'
            )

            # 3. 检查该应用现有的的用户组，是否是默认的三个，如果不是，则删除后重建
            exists_user_group_ids = [
                self.user_group_map[role_key] for role_key in all_role_keys if role_key in self.user_group_map
            ]
            if len(exists_user_group_ids) < len(all_role_keys):
                if exists_user_group_ids:
                    print(f'user groups {exists_user_group_ids} exists, clean them and recreate...')
                    self.cli.delete_user_groups(exists_user_group_ids)
                    ApplicationUserGroup.objects.filter(app_code=app_code).delete()

                groups = self.cli.create_builtin_user_groups(grade_manager_id, app_code)
                for group in groups:
                    role, group_id, group_name = group['role'], group['id'], group['name']
                    print(f'create user group id: {group_id}, role: {ApplicationRole(role).name}, name: {group_name}')

                    # 更新用户组映射表信息 & ApplicationUserGroup 数据
                    self.user_group_map[(app_code, role)] = group_id
                    ApplicationUserGroup.objects.create(app_code=app_code, role=role, user_group_id=group_id)

                # 新创建用户组后，需要对用户组进行授权
                self.cli.grant_user_group_policies(app_code, app_name, groups)

            # 4. 将各类角色同步到权限中心用户组，迁移的权限都是永不过期
            user_group_id = self.user_group_map[administrator_key]
            self.cli.add_user_group_members(user_group_id, administrators, NEVER_EXPIRE_DAYS)
            print(
                f'add user_group (id: {user_group_id}, role: {ApplicationRole.ADMINISTRATOR.name}) members:\n'
                f'count: {len(administrators)}, users: {administrators}'
            )

            if developers := self.members_map[developer_key]:
                user_group_id = self.user_group_map[developer_key]
                self.cli.add_user_group_members(user_group_id, developers, NEVER_EXPIRE_DAYS)
                print(
                    f'add user_group (id: {user_group_id}, role: {ApplicationRole.DEVELOPER.name}) members:\n'
                    f'count: {len(developers)}, users: {developers}'
                )

            if operators := self.members_map[operator_key]:
                user_group_id = self.user_group_map[operator_key]
                self.cli.add_user_group_members(user_group_id, operators, NEVER_EXPIRE_DAYS)
                print(
                    f'add user_group (id: {user_group_id}, role: {ApplicationRole.OPERATOR.name}) members:\n'
                    f'count: {len(operators)}, users: {operators}'
                )

            print(f'migrate application [{app_name}/{app_code}] user role success! {idx}/{self.total_count}\n')

            # 每个应用数据迁移间隔，防止给数据库/权限中心过大压力
            time.sleep(MIGRATE_APP_INTERVAL)

        print(f'---------------- migrate {self.total_count} applications role data finished! ----------------')
