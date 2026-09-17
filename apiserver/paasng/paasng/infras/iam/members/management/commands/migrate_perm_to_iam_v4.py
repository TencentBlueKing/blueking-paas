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

"""把存量应用的成员权限从权限中心 V3 迁移到 V4

现网的成员数据只存在权限中心的用户组里（本地 `ApplicationMembership` 已废弃），因此本命令在
同一进程内读 V3、写 V4：用本地记录的 V3 ID 读出各角色成员，在 V4 建好管理空间与三个内建用户组
并写入成员，最后把本地记录的 ID 原地换成 V4 的新 ID，并把新旧 ID 映射落盘。

V3 与 V4 的授权数据完全隔离，本地表同一行不会并存两版 ID，所以改写是必须的：不换 ID，V4 环境下
所有鉴权与成员操作都会指向不存在的用户组。改写前必须先读完 V3 成员，否则 V3 ID 丢失后无从回查。

几项 V4 侧的限制会体现在迁移结果上：

- 授权有效期上限 365 天（`V4_MAX_PERMISSION_DAYS`），迁移写入的权限一年后到期，平台侧没有续期机制
- 没有空间成员增删接口，管理空间的管理员只能在创建时一次性写齐，迁移后管理员名单变化无法同步到空间
- 迁移期间本地表会处于「部分应用已是 V4 ID、部分仍是 V3 ID」的中间态，须在停服窗口内执行

命令幂等，可重跑：V4 侧同名的管理空间与用户组会被回查复用，本地 ID 以映射文件中记录的 V3 ID 为准。

Examples:

    # 迁移全量应用
    python manage.py migrate_perm_to_iam_v4

    # 只迁移指定应用
    python manage.py migrate_perm_to_iam_v4 --apps app-code-1 app-code-2

    # 只打印待迁移的成员情况，不发起任何写请求
    python manage.py migrate_perm_to_iam_v4 --dry-run

    # 迁移完成后对账，逐角色比对 V3 与 V4 的成员名单
    python manage.py migrate_perm_to_iam_v4 --verify-only

    # 监控/日志尚未接入 V4 的环境，跳过这两个系统的权限范围
    python manage.py migrate_perm_to_iam_v4 --skip-observability-scope
"""

import json
import traceback
from pathlib import Path
from typing import Dict, List

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.infras.iam.base.constants import IAMVersion
from paasng.infras.iam.constants import APP_DEFAULT_ROLES, NEVER_EXPIRE_DAYS
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.infras.iam.shim import get_iam_version
from paasng.infras.iam.v3.management import BKIAMV3ManagementBackend
from paasng.infras.iam.v4.management import BKIAMV4ManagementBackend
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.basic import get_username_by_bkpaas_user_id

# 新旧 ID 映射。重跑时它是 V3 ID 的唯一来源——本地表在首轮迁移后已经换成 V4 ID
DEFAULT_MAPPING_FILE = "./iam_v4_migration_mapping.json"

# 成功与失败记录写在映射文件所在目录，三份产物不分散
SUCCESS_RECORDS_FILENAME = "migrate_iam_v4_success_records.json"
FAILED_RECORDS_FILENAME = "migrate_iam_v4_failed_records.json"


class Command(BaseCommand):
    help = "将存量应用的成员权限从权限中心 V3 迁移到 V4"

    def add_arguments(self, parser):
        parser.add_argument("--apps", dest="app_codes", nargs="*", help="指定应用 code 列表，缺省为全量应用")
        parser.add_argument("--dry-run", action="store_true", help="只打印待迁移的成员情况，不发起写请求")
        parser.add_argument("--verify-only", action="store_true", help="只对账，逐角色比对 V3 与 V4 的成员名单")
        parser.add_argument(
            "--skip-observability-scope",
            action="store_true",
            help="创建管理空间时跳过监控/日志的权限范围，用于这两个系统尚未接入 V4 的环境",
        )
        parser.add_argument("--exclude-users", nargs="*", default=[], help="不迁移的用户名，如已离职的账号")
        parser.add_argument("--mapping-file", default=DEFAULT_MAPPING_FILE, help="新旧 ID 映射的落盘路径")
        parser.add_argument("--operator", default="", help="V4 写操作的操作人，缺省使用系统账号")

    def handle(
        self,
        app_codes: List[str] | None,
        dry_run: bool,
        verify_only: bool,
        skip_observability_scope: bool,
        exclude_users: List[str],
        mapping_file: str,
        operator: str,
        *args,
        **options,
    ):
        self.dry_run = dry_run
        self.skip_observability_scope = skip_observability_scope
        # admin 拥有全量权限，不占用配额也无需授权，与 V4 backend 内部的过滤保持一致
        self.exclude_users = set(exclude_users) | {settings.ADMIN_USERNAME}
        self.mapping_file = Path(mapping_file)
        self.success_records_file = self.mapping_file.parent / SUCCESS_RECORDS_FILENAME
        self.failed_records_file = self.mapping_file.parent / FAILED_RECORDS_FILENAME
        self.operator = operator or None
        self.existing_mapping = self._load_mapping()

        applications = self._load_applications(app_codes)
        if not applications:
            self.stdout.write(self.style.WARNING("没有找到待处理的应用"))
            return

        if verify_only:
            self._verify(applications)
            return

        self._check_iam_version()
        self._migrate(applications)

    # ---------------- 准备 ----------------

    def _check_iam_version(self):
        """本地 ID 会被改写成 V4 的值，在仍以 v3 运行的环境执行等于把该环境的权限数据改坏"""
        if self.dry_run:
            return

        version = get_iam_version()
        if version != IAMVersion.V4:
            raise CommandError(
                f"当前环境的 BK_IAM_VERSION 为 {version.value}，迁移会把本地记录的用户组 ID 改写为 V4 的值，"
                "请先将环境切换为 v4 后再执行；只想预览可加 --dry-run"
            )

    def _load_applications(self, app_codes: List[str] | None) -> List[Application]:
        applications = Application.objects.filter(is_deleted=False)
        if app_codes:
            applications = applications.filter(code__in=app_codes)

        applications = list(applications.order_by("code"))

        if app_codes:
            missing = set(app_codes) - {app.code for app in applications}
            if missing:
                self.stdout.write(self.style.WARNING(f"以下应用不存在或已删除，将被忽略: {sorted(missing)}"))

        return applications

    def _load_mapping(self) -> Dict[str, Dict]:
        """读取已有的映射文件，按应用 code 索引"""
        if not self.mapping_file.exists():
            return {}

        with open(self.mapping_file) as fh:
            records = json.load(fh)

        return {record["app_code"]: record for record in records}

    # ---------------- 迁移 ----------------

    def _migrate(self, applications: List[Application]):
        total = len(applications)
        prefix = "[dry-run] " if self.dry_run else ""
        self.stdout.write(f"{prefix}开始迁移 {total} 个应用的成员权限到权限中心 V4")

        success_records, failed_records, mapping_records = [], [], []

        for idx, application in enumerate(applications, start=1):
            position = f"{idx}/{total} {application.code}"
            try:
                record = self._migrate_single(application)
            except Exception as e:  # noqa: BLE001
                failed_records.append(
                    {"app_code": application.code, "exception": str(e), "traceback": traceback.format_exc()}
                )
                self.stderr.write(self.style.ERROR(f"{prefix}{position}: 迁移失败, {e}"))
                continue

            success_records.append(record)
            if not self.dry_run:
                mapping_records.append(record["mapping"])

            self.stdout.write(f"{prefix}{position}: {self._summarize(record)}")

        self.stdout.write(
            self.style.NOTICE(f"{prefix}迁移结束，成功 {len(success_records)} 个，失败 {len(failed_records)} 个")
        )

        if self.dry_run:
            return

        self._store_mapping(mapping_records)
        self._store_records(self.success_records_file, success_records)
        self._store_records(self.failed_records_file, failed_records)

        if failed_records:
            raise CommandError(f"{len(failed_records)} 个应用迁移失败，详见 {self.failed_records_file}")

    def _migrate_single(self, application: Application) -> Dict:
        app_code = application.code
        tenant_id = get_tenant_id_for_app(app_code)

        # 1. 先把 V3 的成员读全。本地 ID 一旦改写就再也回查不到 V3 侧的数据
        v3_ids = self._resolve_v3_ids(app_code)
        v3_backend = BKIAMV3ManagementBackend(tenant_id)
        managers = self._fetch_v3_managers(v3_backend, v3_ids, application)
        role_members = {
            role: self._exclude(v3_backend.fetch_user_group_members(v3_ids["user_groups"][role]))
            if v3_ids["user_groups"].get(role)
            else []
            for role in APP_DEFAULT_ROLES
        }

        if self.dry_run:
            return {
                "app_code": app_code,
                "managers": managers,
                "members": {ApplicationRole(role).name: members for role, members in role_members.items()},
                "member_failures": [],
            }

        # 2. V4 的管理空间在创建时一次性写齐权限范围与管理员，事后都没有补写的接口
        bk_space_id = None if self.skip_observability_scope else self._resolve_bk_space_id(application)
        v4_backend = BKIAMV4ManagementBackend(tenant_id, self.operator)
        space_id = v4_backend.create_management_space(
            app_code,
            application.name,
            bk_space_id=bk_space_id,
            init_members=managers,
        )

        # 3. 建用户组后逐角色加成员。创建时不带成员，三个角色统一走加成员的链路
        user_groups = v4_backend.create_builtin_user_groups(space_id, app_code, app_name=application.name)
        member_failures = []
        for group in user_groups:
            members = role_members.get(ApplicationRole(group.role), [])
            member_failures.extend(self._add_members(v4_backend, group.id, members, ApplicationRole(group.role)))

        # 4. 本地 ID 换成 V4 的值
        with transaction.atomic():
            self._rewrite_local_ids(app_code, tenant_id, space_id, user_groups)

        return {
            "app_code": app_code,
            "managers": managers,
            "members": {ApplicationRole(role).name: members for role, members in role_members.items()},
            "member_failures": member_failures,
            "mapping": {
                "app_code": app_code,
                "tenant_id": tenant_id,
                "grade_manager": {"v3_id": v3_ids["grade_manager"], "v4_id": space_id},
                "user_groups": [
                    {
                        "role": group.role,
                        "role_name": ApplicationRole(group.role).name,
                        "v3_id": v3_ids["user_groups"].get(ApplicationRole(group.role)),
                        "v4_id": group.id,
                        "member_count": len(role_members.get(ApplicationRole(group.role), [])),
                    }
                    for group in user_groups
                ],
            },
        }

    def _resolve_v3_ids(self, app_code: str) -> Dict:
        """取该应用在 V3 侧的管理空间与用户组 ID

        重跑时本地表存的已经是 V4 的 ID，用它去读 V3 会读到别的应用的数据，
        因此首轮迁移写下的映射文件优先于本地表。
        """
        if record := self.existing_mapping.get(app_code):
            return {
                "grade_manager": record["grade_manager"]["v3_id"],
                "user_groups": {
                    ApplicationRole(group["role"]): group["v3_id"] for group in record["user_groups"] if group["v3_id"]
                },
            }

        grade_manager = ApplicationGradeManager.objects.filter(app_code=app_code).first()
        return {
            "grade_manager": grade_manager.grade_manager_id if grade_manager else None,
            "user_groups": {
                ApplicationRole(group.role): group.user_group_id
                for group in ApplicationUserGroup.objects.filter(app_code=app_code)
            },
        }

    def _fetch_v3_managers(
        self, v3_backend: BKIAMV3ManagementBackend, v3_ids: Dict, application: Application
    ) -> List[str]:
        """取 V3 的分级管理员成员，作为 V4 管理空间的管理员

        V4 要求管理空间的管理员不能为空，没有存量管理员时回退到应用创建者。
        """
        managers = []
        if v3_ids["grade_manager"]:
            managers = self._exclude(v3_backend.fetch_management_space_members(v3_ids["grade_manager"]))

        if managers:
            return managers

        creator = get_username_by_bkpaas_user_id(application.creator)
        self.stdout.write(
            self.style.WARNING(f"  {application.code} 在 V3 侧没有可用的分级管理员，回退为创建者 {creator}")
        )
        return [creator]

    def _resolve_bk_space_id(self, application: Application) -> str:
        """取监控空间的资源 ID，用于把监控/日志的权限范围一次写进管理空间"""
        try:
            space, _ = get_or_create_bk_monitor_space(application)
        except Exception as e:
            raise RuntimeError(
                f"无法获取应用 {application.code} 的蓝鲸监控空间，监控/日志权限范围写不进管理空间。"
                "请确认监控服务可用，或加 --skip-observability-scope 跳过"
            ) from e

        return space.iam_resource_id

    def _add_members(
        self, v4_backend: BKIAMV4ManagementBackend, group_id: int, members: List[str], role: ApplicationRole
    ) -> List[Dict]:
        """把成员加进 V4 用户组，批量失败时降级为逐人重试

        存量数据里会有已离职等无法授权的账号，批量提交时它们会让整批失败。逐人重试能把影响
        收敛到单个用户，其余成员照常迁移。
        """
        if not members:
            return []

        try:
            v4_backend.add_user_group_members(group_id, members, NEVER_EXPIRE_DAYS, operator=self.operator)
        except Exception as e:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"  用户组 {group_id} 批量加成员失败，改为逐人添加: {e}"))
        else:
            return []

        failures = []
        for username in members:
            try:
                v4_backend.add_user_group_members(group_id, [username], NEVER_EXPIRE_DAYS, operator=self.operator)
            except Exception as e:  # noqa: BLE001
                failures.append({"role": role.name, "group_id": group_id, "username": username, "reason": str(e)})

        if failures:
            self.stderr.write(
                self.style.ERROR(
                    f"  用户组 {group_id} 有 {len(failures)} 个成员未能添加: {[item['username'] for item in failures]}"
                )
            )
        return failures

    @staticmethod
    def _rewrite_local_ids(app_code: str, tenant_id: str, space_id: int, user_groups: List) -> None:
        ApplicationGradeManager.objects.filter(app_code=app_code).delete()
        ApplicationGradeManager.objects.create(app_code=app_code, grade_manager_id=space_id, tenant_id=tenant_id)

        for group in user_groups:
            ApplicationUserGroup.objects.update_or_create(
                app_code=app_code,
                role=group.role,
                defaults={"user_group_id": group.id, "tenant_id": tenant_id},
            )

    # ---------------- 对账 ----------------

    def _verify(self, applications: List[Application]):
        total = len(applications)
        self.stdout.write(f"开始对账 {total} 个应用在 V3 与 V4 的成员名单")

        identical, diff_app_codes, unknown_app_codes, failed_app_codes = 0, [], [], []

        for idx, application in enumerate(applications, start=1):
            position = f"{idx}/{total} {application.code}"

            record = self.existing_mapping.get(application.code)
            if not record:
                unknown_app_codes.append(application.code)
                self.stdout.write(self.style.WARNING(f"{position}: 映射文件中没有迁移记录，无法对账"))
                continue

            try:
                diffs = self._diff_single(application.code, record)
            except Exception as e:  # noqa: BLE001
                failed_app_codes.append(application.code)
                self.stderr.write(self.style.ERROR(f"{position}: 对账失败, {e}"))
                continue

            if not diffs:
                identical += 1
                self.stdout.write(f"{position}: 一致")
                continue

            diff_app_codes.append(application.code)
            self.stdout.write(self.style.ERROR(f"{position}: 存在差异"))
            for diff in diffs:
                self.stdout.write(
                    f"  [{diff['scope']}] V3 有而 V4 缺: {diff['missing']}; V4 有而 V3 无: {diff['extra']}"
                )

        self.stdout.write(
            self.style.NOTICE(
                f"对账结束，总计 {total} 个，一致 {identical} 个，有差异 {len(diff_app_codes)} 个，"
                f"无迁移记录 {len(unknown_app_codes)} 个，失败 {len(failed_app_codes)} 个"
            )
        )

        if diff_app_codes or unknown_app_codes or failed_app_codes:
            raise CommandError(
                f"有差异: {diff_app_codes}, 无迁移记录: {unknown_app_codes}, 对账失败: {failed_app_codes}"
            )

    def _diff_single(self, app_code: str, record: Dict) -> List[Dict]:
        tenant_id = record.get("tenant_id") or get_tenant_id_for_app(app_code)
        v3_backend = BKIAMV3ManagementBackend(tenant_id)
        v4_backend = BKIAMV4ManagementBackend(tenant_id, self.operator)

        diffs = []

        # 管理空间：V3 的分级管理员成员对应 V4 的空间管理员
        grade_manager = record["grade_manager"]
        if grade_manager["v3_id"]:
            diff = self._diff_members(
                "管理空间",
                self._exclude(v3_backend.fetch_management_space_members(grade_manager["v3_id"])),
                self._exclude(v4_backend.fetch_management_space_members(grade_manager["v4_id"])),
            )
            if diff:
                diffs.append(diff)

        for group in record["user_groups"]:
            if not group["v3_id"]:
                continue

            diff = self._diff_members(
                group["role_name"],
                self._exclude(v3_backend.fetch_user_group_members(group["v3_id"])),
                self._exclude(v4_backend.fetch_user_group_members(group["v4_id"])),
            )
            if diff:
                diffs.append(diff)

        return diffs

    @staticmethod
    def _diff_members(scope: str, v3_members: List[str], v4_members: List[str]) -> Dict | None:
        v3_set, v4_set = set(v3_members), set(v4_members)
        missing, extra = sorted(v3_set - v4_set), sorted(v4_set - v3_set)
        if not (missing or extra):
            return None

        return {"scope": scope, "missing": missing, "extra": extra}

    # ---------------- 输出 ----------------

    def _exclude(self, usernames: List[str]) -> List[str]:
        return [username for username in usernames if username not in self.exclude_users]

    @staticmethod
    def _summarize(record: Dict) -> str:
        members = ", ".join(f"{role}={len(usernames)}" for role, usernames in record["members"].items())
        summary = f"管理员 {len(record['managers'])} 人, 成员 {members}"
        if failures := record["member_failures"]:
            summary = f"{summary}, {len(failures)} 个成员添加失败"
        return summary

    def _store_mapping(self, mapping_records: List[Dict]):
        """映射按应用 code 合并写回，只跑了部分应用时不会冲掉其他应用的记录"""
        merged: Dict[str, Dict] = dict(self.existing_mapping)
        for record in mapping_records:
            merged[record["app_code"]] = record

        self._write_json(self.mapping_file, [merged[app_code] for app_code in sorted(merged)])
        self.stdout.write(f"新旧 ID 映射已写入 {self.mapping_file}")

    def _store_records(self, path: Path, records: List[Dict]):
        self._write_json(path, records)
        self.stdout.write(f"{len(records)} 条记录已写入 {path}")

    @staticmethod
    def _write_json(path: Path, payload: List[Dict]):
        path.write_text(json.dumps(payload, indent=4, ensure_ascii=False))
