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

import json
import traceback
from collections import defaultdict
from typing import Dict, List

from django.core.management.base import BaseCommand

from paasng.infras.iam.client import BKIAMClient
from paasng.infras.iam.constants import NEVER_EXPIRE_DAYS
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application, ApplicationMembership
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.basic import get_username_by_bkpaas_user_id

# 打印应用 ID 信息时，每行展示数量
PRE_LINE_LIMIT = 15


class Command(BaseCommand):
    """
    蓝鲸应用成员关系迁移到权限中心命令行工具

    使用示例：
    python manage.py migrate_bkpaas3_perm                               # 迁移全量数据
    python manage.py migrate_bkpaas3_perm --dry-run                     # 仅打印待迁移的权限数据信息
    python manage.py migrate_bkpaas3_perm --apps app_code1 app_code2    # 迁移指定的应用权限数据
    python manage.py migrate_bkpaas3_perm --exclude-users user1 user2   # 迁移过程中，指定的用户不会被添加为分级管理员
    """

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", help="dry run only", action="store_true")
        parser.add_argument("--apps", nargs="*", help="specified app code list")
        parser.add_argument("--exclude-users", nargs="*", help="user skip add as grade manager")
        parser.set_defaults(is_enabled=True)

    def handle(self, dry_run, apps, exclude_users, *args, **options):
        self.dry_run: bool = dry_run
        self.apps: List[str] = apps
        self.exclude_users: List[str] = exclude_users or []

        self._prepare()
        self._migrate()
        self._store_records()

    def _prepare(self):
        """中间态数据准备"""
        print("------------------ start data preparation -----------------")

        applications = Application.objects.filter(is_deleted=False)
        grade_managers = ApplicationGradeManager.objects.all()
        user_groups = ApplicationUserGroup.objects.all()
        memberships = ApplicationMembership.objects.select_related("application").all()

        if self.apps:
            applications = applications.filter(code__in=self.apps)
            grade_managers = grade_managers.filter(app_code__in=self.apps)
            user_groups = user_groups.filter(app_code__in=self.apps)
            memberships = memberships.filter(application__code__in=self.apps)

        # 待迁移应用数据
        self.applications = [
            {
                "id": str(app.id),
                "code": app.code,
                "name": app.name,
                "creator": get_username_by_bkpaas_user_id(app.creator),
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

        print(f"{self.total_count} applications waiting for migrate:")

        for start_at in range(0, self.total_count, PRE_LINE_LIMIT):
            end_at = start_at + PRE_LINE_LIMIT
            end_at = end_at if end_at < self.total_count else self.total_count
            print(
                f"{start_at+1} - {end_at}:".rjust(11),
                " ".join([app["code"] for app in self.applications[start_at:end_at]]),
            )

        print("---------------- data preparation finished ----------------")

    def _migrate(self):
        """迁移权限数据"""
        if self.dry_run:
            print("------------------------- DRY-RUN -------------------------")
            return

        print("---------------- start migrate applications role data ----------------")

        self.success_records = []
        self.failed_records = []

        for idx, app in enumerate(self.applications, start=1):
            status, flag = "success", "."
            try:
                logs = self._migrate_single(idx, app)
            except Exception as e:
                self.failed_records.append(
                    {
                        "idx": idx,
                        "app": app,
                        "exception": str(e),
                        "traceback": traceback.format_exc(),
                    }
                )
                status, flag = "failed", "F"
            else:
                self.success_records.append({"idx": idx, "app": app, "logs": logs})

            print(f"{flag} {idx}/{self.total_count} migrate app [{app['name']}/{app['code']}] user roles {status}")

        print(f"---------------- migrate {self.total_count} applications role data finished! ----------------")
        print(f"-------------- success: {len(self.success_records)} failed: {len(self.failed_records)} --------------")

    def _migrate_single(self, idx: int, app: Dict) -> List:  # noqa: C901, PLR0912, PLR0915
        """迁移单个应用权限数据"""
        app_code, app_name, creator = app["code"], app["name"], app["creator"]
        tenant_id = get_tenant_id_for_app(app_code)
        iam_client = BKIAMClient(tenant_id)
        migrate_logs = []

        administrator_key = (app_code, ApplicationRole.ADMINISTRATOR)
        developer_key = (app_code, ApplicationRole.DEVELOPER)
        operator_key = (app_code, ApplicationRole.OPERATOR)
        all_role_keys = [administrator_key, developer_key, operator_key]

        migrate_logs.append(
            f"start migrate application [{app_name}/{app_code}] user roles... {idx}/{self.total_count}"
        )

        administrators = self.members_map[administrator_key]
        if not administrators:
            raise ValueError("application hasn't administrators")

        # 默认创建者会是应用的分级管理员，如果他已经不是应用的管理员，则使用第一个应用管理员，作为初始的分级管理员
        first_grade_manager = creator
        if creator not in administrators:
            first_grade_manager = administrators[0]
            migrate_logs.append(f"creator not app's administrators, use first administrator {first_grade_manager}")

        # 1。检查有没有该应用的分级管理员信息，如果没有，则需要创建
        grade_manager_id = self.grade_manager_map.get(app_code)
        if not grade_manager_id:
            migrate_logs.append("grade manager not exists, create...")
            if first_grade_manager in self.exclude_users:
                first_grade_manager = None
                migrate_logs.append(f"{first_grade_manager} in exclude users, skip add as members...")
            else:
                migrate_logs.append(f"add {first_grade_manager} as grade manager members...")

            grade_manager_id = iam_client.create_grade_managers(app_code, app_name, first_grade_manager)

            # 更新分级管理员映射表信息 & ApplicationGradeManager 表数据
            self.grade_manager_map[app_code] = grade_manager_id
            ApplicationGradeManager.objects.create(app_code=app_code, grade_manager_id=grade_manager_id)

        # 2. 获取具有管理员身份的用户名，如果没有，则默认将创建者添加为分级管理员（拥有审批加入用户组权限）
        migrate_logs.append(
            f"add grade manager (id: {grade_manager_id}) members: "
            f"count: {len(administrators)}, users: {administrators}"
        )
        # 由于数据库中会存在已经离职的用户，无法加入到权限中心，按权限中心建议，使用 for 循环单个单个添加，忽略但记录异常
        for username in administrators:
            if username in self.exclude_users:
                migrate_logs.append(f"user {username} in exclude user list, skip add as grade manager")
                continue
            try:
                iam_client.add_grade_manager_members(grade_manager_id, [username])
            except Exception as e:
                migrate_logs.append(f"failed to add grade manager: {username}, maybe was resigned: {str(e)}")

        # 3. 检查该应用现有的的用户组，是否是默认的三个，如果不是，则删除后重建
        exists_user_group_ids = [
            self.user_group_map[role_key] for role_key in all_role_keys if role_key in self.user_group_map
        ]
        if len(exists_user_group_ids) < len(all_role_keys):
            if exists_user_group_ids:
                migrate_logs.append(f"user groups {exists_user_group_ids} exists, clean them and recreate...")
                iam_client.delete_user_groups(exists_user_group_ids)
                ApplicationUserGroup.objects.filter(app_code=app_code).delete()

            groups = iam_client.create_builtin_user_groups(grade_manager_id, app_code)
            for group in groups:
                role, group_id, group_name = group["role"], group["id"], group["name"]
                migrate_logs.append(
                    f"create user group id: {group_id}, role: {ApplicationRole(role).name}, name: {group_name}"
                )

                # 更新用户组映射表信息 & ApplicationUserGroup 数据
                self.user_group_map[(app_code, role)] = group_id
                ApplicationUserGroup.objects.create(app_code=app_code, role=role, user_group_id=group_id)

            # 新创建用户组后，需要对用户组进行授权
            iam_client.grant_user_group_policies(app_code, app_name, groups)

        # 4. 将各类角色同步到权限中心用户组，迁移的权限都是永不过期
        user_group_id = self.user_group_map[administrator_key]
        migrate_logs.append(
            f"try add user_group (id: {user_group_id}, role: {ApplicationRole.ADMINISTRATOR.name}) members..."
            f"count: {len(administrators)}, users: {administrators}"
        )

        for username in administrators:
            try:
                iam_client.add_user_group_members(user_group_id, [username], NEVER_EXPIRE_DAYS)
            except Exception as e:
                migrate_logs.append(f"failed to add app administrator: {username}, maybe was resigned: {str(e)}")

        if developers := self.members_map[developer_key]:
            user_group_id = self.user_group_map[developer_key]
            migrate_logs.append(
                f"try add user_group (id: {user_group_id}, role: {ApplicationRole.DEVELOPER.name}) members..."
                f"count: {len(developers)}, users: {developers}"
            )

            for username in developers:
                try:
                    iam_client.add_user_group_members(user_group_id, [username], NEVER_EXPIRE_DAYS)
                except Exception as e:
                    migrate_logs.append(f"failed to add app developer: {username}, maybe was resigned: {str(e)}")

        if operators := self.members_map[operator_key]:
            user_group_id = self.user_group_map[operator_key]
            migrate_logs.append(
                f"try add user_group (id: {user_group_id}, role: {ApplicationRole.OPERATOR.name}) members..."
                f"count: {len(operators)}, users: {operators}"
            )

            for username in operators:
                try:
                    iam_client.add_user_group_members(user_group_id, [username], NEVER_EXPIRE_DAYS)
                except Exception as e:
                    migrate_logs.append(f"failed to add app operator: {username}, maybe was resigned: {str(e)}")

        migrate_logs.append(f"migrate application [{app_name}/{app_code}] user role success! {idx}/{self.total_count}")

        return migrate_logs

    def _store_records(self):
        if self.dry_run:
            return

        print("---------------- store records to local files ----------------")

        with open("./migrate_success_records.json", "w") as fw:
            fw.write(json.dumps(self.success_records, indent=4, ensure_ascii=False))

        with open("./migrate_failed_records.json", "w") as fw:
            fw.write(json.dumps(self.failed_records, indent=4, ensure_ascii=False))

        print("---------------- store records finished! ----------------")
