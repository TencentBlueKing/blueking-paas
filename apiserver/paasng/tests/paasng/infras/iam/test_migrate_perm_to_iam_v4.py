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

import json
from io import StringIO
from pathlib import Path
from typing import Dict, List
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from paasng.infras.iam import utils
from paasng.infras.iam.base.dto import UserGroup
from paasng.infras.iam.constants import APP_DEFAULT_ROLES
from paasng.infras.iam.exceptions import BKIAMApiError
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

COMMAND = "migrate_perm_to_iam_v4"
COMMAND_MODULE = "paasng.infras.iam.members.management.commands.migrate_perm_to_iam_v4"

# V3 侧的 ID，由 setup 时写进本地表
V3_SPACE_ID = 101
V3_GROUP_IDS = {ApplicationRole.ADMINISTRATOR: 201, ApplicationRole.DEVELOPER: 202, ApplicationRole.OPERATOR: 203}

# V4 侧的 ID，由 mock 的 V4 backend 返回
V4_SPACE_ID = 901
V4_GROUP_IDS = {ApplicationRole.ADMINISTRATOR: 902, ApplicationRole.DEVELOPER: 903, ApplicationRole.OPERATOR: 904}

# V3 侧各角色的存量成员
V3_MEMBERS = {
    ApplicationRole.ADMINISTRATOR: ["admin1"],
    ApplicationRole.DEVELOPER: ["dev1", "dev2"],
    ApplicationRole.OPERATOR: ["ops1"],
}


def _create_app_with_v3_perm(settings) -> Application:
    """造一个已在 V3 侧注册过权限的应用

    应用先在 v3 配置下创建（走 stub 的 V3 客户端），再把环境切回 v4，模拟迁移窗口的状态。
    创建时信号已写过一批 stub ID，这里换成固定值，便于断言迁移前后的变化。
    """
    settings.BK_IAM_VERSION = "v3"
    application = create_app()

    ApplicationGradeManager.objects.filter(app_code=application.code).delete()
    ApplicationUserGroup.objects.filter(app_code=application.code).delete()

    ApplicationGradeManager.objects.create(
        app_code=application.code, grade_manager_id=V3_SPACE_ID, tenant_id=application.tenant_id
    )
    for role, group_id in V3_GROUP_IDS.items():
        ApplicationUserGroup.objects.create(
            app_code=application.code, role=int(role), user_group_id=group_id, tenant_id=application.tenant_id
        )

    settings.BK_IAM_VERSION = "v4"
    return application


class MigrateRunner:
    """调用命令，三份产物统一落在临时目录"""

    def __init__(self, mapping_file: Path):
        self.mapping_file = mapping_file
        self.stdout = StringIO()
        self.stderr = StringIO()

    def __call__(self, *args) -> str:
        call_command(COMMAND, *args, mapping_file=str(self.mapping_file), stdout=self.stdout, stderr=self.stderr)
        return self.output

    @property
    def output(self) -> str:
        return self.stdout.getvalue()

    def read_json(self, filename: str) -> List[Dict]:
        return json.loads((self.mapping_file.parent / filename).read_text())


@pytest.fixture()
def migrate(tmp_path) -> MigrateRunner:
    return MigrateRunner(tmp_path / "mapping.json")


@pytest.fixture()
def bk_app_with_v3_perm(settings) -> Application:
    return _create_app_with_v3_perm(settings)


@pytest.fixture()
def v3_backend() -> mock.Mock:
    by_group_id = {V3_GROUP_IDS[role]: usernames for role, usernames in V3_MEMBERS.items()}

    backend = mock.Mock()
    # admin 拥有全量权限，不该被迁移，命令需要把它过滤掉
    backend.fetch_management_space_members.return_value = ["admin1", "admin"]
    backend.fetch_user_group_members.side_effect = lambda group_id: list(by_group_id.get(group_id, []))
    return backend


@pytest.fixture()
def v4_backend(bk_app_with_v3_perm) -> mock.Mock:
    backend = mock.Mock()
    backend.create_management_space.return_value = V4_SPACE_ID
    backend.create_builtin_user_groups.return_value = [
        UserGroup(
            id=V4_GROUP_IDS[role],
            name=utils.gen_user_group_name(bk_app_with_v3_perm.code, role),
            role=int(role),
            description=utils.gen_user_group_desc(bk_app_with_v3_perm.code, role),
        )
        for role in APP_DEFAULT_ROLES
    ]
    return backend


@pytest.fixture()
def _mock_backends(v3_backend, v4_backend):
    """把命令内部构造的两个 backend 与监控空间查询换成 mock"""
    with (
        mock.patch(f"{COMMAND_MODULE}.BKIAMV3ManagementBackend", return_value=v3_backend),
        mock.patch(f"{COMMAND_MODULE}.BKIAMV4ManagementBackend", return_value=v4_backend),
        mock.patch(
            f"{COMMAND_MODULE}.get_or_create_bk_monitor_space",
            return_value=(mock.Mock(iam_resource_id="-100"), False),
        ),
    ):
        yield


def _added_members(v4_backend: mock.Mock) -> Dict[int, List[str]]:
    return {call.args[0]: call.args[1] for call in v4_backend.add_user_group_members.call_args_list}


@pytest.mark.usefixtures("_mock_backends")
class TestMigrate:
    def test_migrates_members_and_rewrites_local_ids(self, migrate, bk_app_with_v3_perm, v4_backend):
        app_code = bk_app_with_v3_perm.code

        migrate()

        # 管理空间的管理员只能在创建时写齐
        kwargs = v4_backend.create_management_space.call_args.kwargs
        assert kwargs["init_members"] == ["admin1"]
        assert kwargs["bk_space_id"] == "-100"

        assert _added_members(v4_backend) == {
            V4_GROUP_IDS[ApplicationRole.ADMINISTRATOR]: ["admin1"],
            V4_GROUP_IDS[ApplicationRole.DEVELOPER]: ["dev1", "dev2"],
            V4_GROUP_IDS[ApplicationRole.OPERATOR]: ["ops1"],
        }

        # 本地记录换成 V4 的 ID，否则 V4 环境下所有成员操作都会指向不存在的用户组
        assert ApplicationGradeManager.objects.get(app_code=app_code).grade_manager_id == V4_SPACE_ID
        assert {
            ApplicationRole(group.role): group.user_group_id
            for group in ApplicationUserGroup.objects.filter(app_code=app_code)
        } == V4_GROUP_IDS

    def test_mapping_file_keeps_both_ids(self, migrate, bk_app_with_v3_perm):
        migrate()

        records = migrate.read_json("mapping.json")
        assert len(records) == 1

        record = records[0]
        assert record["app_code"] == bk_app_with_v3_perm.code
        assert record["grade_manager"] == {"v3_id": V3_SPACE_ID, "v4_id": V4_SPACE_ID}
        assert {group["role_name"]: (group["v3_id"], group["v4_id"]) for group in record["user_groups"]} == {
            role.name: (V3_GROUP_IDS[role], V4_GROUP_IDS[role]) for role in APP_DEFAULT_ROLES
        }

    def test_rerun_reads_v3_ids_from_mapping_file(self, migrate, bk_app_with_v3_perm, v3_backend):
        """重跑时本地表存的已是 V4 ID，V3 ID 只能从映射文件取"""
        migrate()
        v3_backend.reset_mock()

        migrate()

        v3_backend.fetch_management_space_members.assert_called_once_with(V3_SPACE_ID)
        assert {call.args[0] for call in v3_backend.fetch_user_group_members.call_args_list} == set(
            V3_GROUP_IDS.values()
        )

    def test_only_migrates_specified_apps(self, migrate, settings, bk_app_with_v3_perm):
        other = _create_app_with_v3_perm(settings)

        migrate("--apps", bk_app_with_v3_perm.code)

        assert ApplicationGradeManager.objects.get(app_code=bk_app_with_v3_perm.code).grade_manager_id == V4_SPACE_ID
        # 未指定的应用不受影响，本地 ID 仍是 V3 的值
        assert ApplicationGradeManager.objects.get(app_code=other.code).grade_manager_id == V3_SPACE_ID

    def test_skip_observability_scope(self, migrate, bk_app_with_v3_perm, v4_backend):
        migrate("--skip-observability-scope")

        assert v4_backend.create_management_space.call_args.kwargs["bk_space_id"] is None

    def test_exclude_users_are_not_migrated(self, migrate, bk_app_with_v3_perm, v4_backend):
        migrate("--exclude-users", "dev2")

        assert _added_members(v4_backend)[V4_GROUP_IDS[ApplicationRole.DEVELOPER]] == ["dev1"]


@pytest.mark.usefixtures("_mock_backends")
class TestDryRun:
    def test_makes_no_write_at_all(self, migrate, bk_app_with_v3_perm, v4_backend):
        output = migrate("--dry-run")

        v4_backend.create_management_space.assert_not_called()
        v4_backend.create_builtin_user_groups.assert_not_called()
        v4_backend.add_user_group_members.assert_not_called()

        assert ApplicationGradeManager.objects.get(app_code=bk_app_with_v3_perm.code).grade_manager_id == V3_SPACE_ID
        assert not migrate.mapping_file.exists()
        assert "[dry-run]" in output

    def test_allowed_when_env_still_runs_v3(self, migrate, settings, bk_app_with_v3_perm):
        settings.BK_IAM_VERSION = "v3"

        migrate("--dry-run")

    def test_refuses_to_rewrite_ids_when_env_still_runs_v3(self, migrate, settings, bk_app_with_v3_perm):
        settings.BK_IAM_VERSION = "v3"

        with pytest.raises(CommandError, match="BK_IAM_VERSION"):
            migrate()

        assert ApplicationGradeManager.objects.get(app_code=bk_app_with_v3_perm.code).grade_manager_id == V3_SPACE_ID


@pytest.mark.usefixtures("_mock_backends")
class TestMemberFailureTolerance:
    def test_falls_back_to_adding_one_by_one(self, migrate, bk_app_with_v3_perm, v4_backend):
        """批量加成员失败时逐人重试，把影响收敛到单个失效账号"""

        def add_members(group_id, usernames, expired_after_days, operator=None):
            if len(usernames) > 1:
                raise BKIAMApiError("batch add failed")
            if usernames[0] == "dev2":
                raise BKIAMApiError("user not found")

        v4_backend.add_user_group_members.side_effect = add_members

        migrate()

        # dev1 单独重试成功，只有 dev2 被记为失败
        retried = [call.args[1] for call in v4_backend.add_user_group_members.call_args_list]
        assert ["dev1"] in retried
        assert ["dev2"] in retried

        failures = migrate.read_json("migrate_iam_v4_success_records.json")[0]["member_failures"]
        assert [item["username"] for item in failures] == ["dev2"]

        # 单个成员失败不影响本地 ID 改写
        assert ApplicationGradeManager.objects.get(app_code=bk_app_with_v3_perm.code).grade_manager_id == V4_SPACE_ID


@pytest.mark.usefixtures("_mock_backends")
class TestVerifyOnly:
    def test_reports_identical(self, migrate, bk_app_with_v3_perm, v4_backend):
        migrate()

        v4_backend.fetch_management_space_members.return_value = ["admin1"]
        v4_backend.fetch_user_group_members.side_effect = lambda group_id: {
            V4_GROUP_IDS[role]: list(members) for role, members in V3_MEMBERS.items()
        }[group_id]

        assert "一致" in migrate("--verify-only")

    def test_reports_missing_members(self, migrate, bk_app_with_v3_perm, v4_backend):
        migrate()

        v4_backend.fetch_management_space_members.return_value = ["admin1"]
        # V4 的开发者组少了 dev2
        v4_backend.fetch_user_group_members.side_effect = lambda group_id: (
            ["dev1"] if group_id == V4_GROUP_IDS[ApplicationRole.DEVELOPER] else []
        )

        with pytest.raises(CommandError, match="有差异"):
            migrate("--verify-only")

        assert "DEVELOPER" in migrate.output
        assert "dev2" in migrate.output

    def test_app_without_migration_record_is_not_silently_passed(self, migrate, bk_app_with_v3_perm):
        with pytest.raises(CommandError, match="无迁移记录"):
            migrate("--verify-only")

        assert "没有迁移记录" in migrate.output
