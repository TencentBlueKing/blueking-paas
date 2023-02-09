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
import json
import traceback
from typing import List, Tuple

from django.core.management.base import BaseCommand

from paasng.accessories.iam.client import BKIAMClient
from paasng.accessories.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application
from paasng.utils.basic import get_username_by_bkpaas_user_id

# 打印应用 ID 信息时，每行展示数量
PRE_LINE_LIMIT = 15


class Command(BaseCommand):
    """
    蓝鲸应用成员关系迁移到权限中心命令行工具

    使用示例：
    python manage.py sync_iam_admin_members                               # 迁移全量数据
    python manage.py sync_iam_admin_members --dry-run                     # 仅打印待同步的应用信息
    python manage.py sync_iam_admin_members --apps app_code1 app_code2    # 同步指定的应用数据
    python manage.py sync_iam_admin_members --exclude-users user1 user2   # 同步过程中，指定的用户不会被添加为分级管理员
    """

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', help='dry run only', action='store_true')
        parser.add_argument('--apps', nargs='*', help='specified app code list')
        parser.add_argument('--exclude-users', nargs='*', help='user skip add as grade manager')
        parser.set_defaults(is_enabled=True)

    def handle(self, dry_run, apps, exclude_users, *args, **options):
        self.dry_run: bool = dry_run
        self.apps: List[str] = apps
        self.exclude_users: List[str] = exclude_users or []
        self.cli = BKIAMClient()

        self._prepare()
        self._sync()
        self._store_records()

    def _prepare(self):
        """中间态数据准备"""
        print('------------------ start data preparation -----------------')

        applications = Application.objects.filter(is_deleted=False)
        grade_managers = ApplicationGradeManager.objects.all()
        user_groups = ApplicationUserGroup.objects.all()

        if self.apps:
            applications = applications.filter(code__in=self.apps)
            grade_managers = grade_managers.filter(app_code__in=self.apps)
            user_groups = user_groups.filter(app_code__in=self.apps, role=ApplicationRole.ADMINISTRATOR)

        # 应用 => 创建者
        self.app_creator_map = {app.code: get_username_by_bkpaas_user_id(app.creator) for app in applications}
        # 应用 => 分级管理员 ID
        self.grade_manager_map = {m.app_code: m.grade_manager_id for m in grade_managers}
        # 应用 => 管理员用户组 ID
        self.user_group_map = {g.app_code: g.user_group_id for g in user_groups}

        if len(self.grade_manager_map) != len(self.user_group_map):
            raise Exception('the length of grade_manager_map and user_group_map not equal!')

        self.total_count = len(self.user_group_map)
        self.app_codes = list(self.user_group_map)

        print(f'{self.total_count} applications waiting for sync:')

        for start_at in range(0, self.total_count, PRE_LINE_LIMIT):
            end_at = start_at + PRE_LINE_LIMIT
            end_at = end_at if end_at < self.total_count else self.total_count
            print(f'{start_at + 1} - {end_at}:'.rjust(11), ' '.join(self.app_codes[start_at:end_at]))

        print('---------------- data preparation finished ----------------')

    def _sync(self):
        """同步分级管理员与管理员用户组成员"""
        if self.dry_run:
            print('------------------------- DRY-RUN -------------------------')
            return

        self.success_records = []
        self.failed_records = []

        print('---------------- start sync applications administrator ----------------')

        unchanged_cnt = 0
        for idx, app_code in enumerate(self.app_codes, start=1):
            status, flag = 'success', '.'
            try:
                logs, unchanged = self._sync_single(idx, app_code)
                if unchanged:
                    unchanged_cnt += 1
            except Exception as e:
                self.failed_records.append(
                    {
                        'idx': idx,
                        'app_code': app_code,
                        'exception': str(e),
                        'traceback': traceback.format_exc(),
                    }
                )
                status, flag = 'failed', 'F'
            else:
                self.success_records.append({'idx': idx, 'app_code': app_code, 'logs': logs})

            print(f"{flag} {idx}/{self.total_count} sync app {app_code} admin members {status}")

        print(f'---------------- sync {self.total_count} applications administrator finished! ----------------')
        print(
            f'-- success: {len(self.success_records)} '
            f'failed: {len(self.failed_records)} '
            f'unchanged: {unchanged_cnt} --'
        )

    def _sync_single(self, idx: int, app_code: str) -> Tuple[List, bool]:
        """同步单个应用的管理员/分级管理员"""
        sync_logs, unchanged = [], True

        sync_logs.append(f'start sync application {app_code} admin members...')

        user_group_id = self.user_group_map.get(app_code)
        if not user_group_id:
            raise Exception(f'app {app_code} user group id not find!')

        administrators = self.cli.fetch_user_group_members(user_group_id)

        grade_manager_id = self.grade_manager_map.get(app_code)
        if not grade_manager_id:
            raise Exception(f'app {app_code} grade manager id not find!')

        grade_managers = self.cli.fetch_grade_manager_members(grade_manager_id)

        sync_logs.append(f'app_code: {app_code}, user_group_id: {user_group_id}, grade_manager_id: {grade_manager_id}')

        # 待移除的分级管理员（不是应用管理员的，都删掉）
        if usernames := list(set(grade_managers) - set(administrators)):
            sync_logs.append(f"remove {len(usernames)} user from grade manager: {usernames}")
            self.cli.delete_grade_manager_members(grade_manager_id, usernames)
            unchanged = False
        else:
            sync_logs.append('no users need to be remove from grade manager')

        # 待添加为分级管理员的成员
        if usernames := list(set(administrators) - set(grade_managers)):
            sync_logs.append(f"try add {len(usernames)} user as grade manager: {usernames}")
            for user in usernames:
                if user in self.exclude_users:
                    sync_logs.append(f'user {user} in exclude user list, skip add as grade manager')
                    continue
                try:
                    self.cli.add_grade_manager_members(grade_manager_id, [user])
                    unchanged = False
                except Exception as e:
                    sync_logs.append(f'failed to add grade manager: {user}, maybe was resigned: {str(e)}')
        else:
            sync_logs.append('no users need to be added as grade manager')

        if unchanged:
            sync_logs.append(f'nothing changed for app {app_code} after sync...')
        sync_logs.append(f'sync application {app_code} admin members success! {idx}/{self.total_count}')

        return sync_logs, unchanged

    def _store_records(self):
        if self.dry_run:
            return

        print('---------------- store records to local files ----------------')

        with open('./sync_success_records.json', 'w') as fw:
            fw.write(json.dumps(self.success_records, indent=4, ensure_ascii=False))

        with open('./sync_failed_records.json', 'w') as fw:
            fw.write(json.dumps(self.failed_records, indent=4, ensure_ascii=False))

        print('---------------- store records finished! ----------------')
