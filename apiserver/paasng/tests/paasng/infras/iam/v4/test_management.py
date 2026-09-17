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

import time
from http import HTTPStatus
from typing import Any, Dict, List
from unittest import mock

import pytest

from paasng.infras.iam import utils
from paasng.infras.iam.base.constants import V4_MAX_PERMISSION_DAYS
from paasng.infras.iam.constants import (
    APP_DEFAULT_ROLES,
    BK_LOG_SYSTEM_ID,
    BK_MONITOR_SYSTEM_ID,
    NEVER_EXPIRE_DAYS,
    ONE_DAY_SECONDS,
)
from paasng.infras.iam.exceptions import (
    BKIAMApiHTTPError,
    BKIAMCapabilityNotSupportedError,
)
from paasng.infras.iam.permissions.resources.application import AppAction, AppRole
from paasng.infras.iam.v4.management import BKIAMV4ManagementBackend
from paasng.infras.iam.v4.spaces import SPACE_OPERATOR_ROLE_ID
from paasng.platform.applications.constants import ApplicationRole


@pytest.fixture()
def backend(settings) -> BKIAMV4ManagementBackend:
    settings.IAM_PAAS_V3_SYSTEM_ID = "bk_paas3"
    return BKIAMV4ManagementBackend("tenant-foo", operator="creator")


def _group_name(app_code: str, role: ApplicationRole) -> str:
    return utils.gen_user_group_name(app_code, role)


class TestCreateManagementSpace:
    def test_writes_three_systems_and_operator(self, backend):
        """创建时一次性写入三个系统的权限范围，且写操作携带操作人"""
        backend.call = mock.Mock(return_value={"data": {"id": 42}})  # type: ignore

        assert backend.create_management_space("app-code", "App", ["someone"], bk_space_id="-100") == 42

        backend.call.assert_called_once()
        kwargs = backend.call.call_args.kwargs
        assert kwargs["for_write"] is True
        assert kwargs["path_params"] == {"system_id": "bk_paas3"}
        assert kwargs["data"]["managers"] == ["someone"]
        assert kwargs["data"]["subject_scope"] == {"users": ["*"]}
        assert kwargs["data"]["name"] == utils.gen_grade_manager_name("app-code")

        scopes = kwargs["data"]["permission_scope"]
        systems = {item["system"] for item in scopes}
        assert systems == {"bk_paas3", BK_MONITOR_SYSTEM_ID, BK_LOG_SYSTEM_ID}
        observability = [item for item in scopes if item["system"] in {BK_MONITOR_SYSTEM_ID, BK_LOG_SYSTEM_ID}]
        assert {item["id"] for item in observability} == {SPACE_OPERATOR_ROLE_ID}

    def test_writes_all_init_members(self, backend):
        backend.call = mock.Mock(return_value={"data": {"id": 1}})  # type: ignore

        backend.create_management_space("app-code", "App", ["alice", "bob"])

        assert backend.call.call_args.kwargs["data"]["managers"] == ["alice", "bob"]

    def test_without_bk_space_id_only_writes_paas(self, backend):
        backend.call = mock.Mock(return_value={"data": {"id": 1}})  # type: ignore

        backend.create_management_space("app-code", "App", ["someone"])

        systems = {item["system"] for item in backend.call.call_args.kwargs["data"]["permission_scope"]}
        assert systems == {"bk_paas3"}

    def test_conflict_reuses_existing_space_id(self, backend):
        """同名空间已存在时回查并复用 ID，不抛未处理异常"""
        backend.call = mock.Mock(  # type: ignore
            side_effect=BKIAMApiHTTPError(
                "space already exists", status_code=HTTPStatus.CONFLICT, request_id="req-409"
            )
        )
        existing_name = utils.gen_grade_manager_name("app-code")
        backend.paginate = mock.Mock(  # type: ignore
            return_value=iter([{"id": 7, "name": existing_name}, {"id": 8, "name": "other"}])
        )

        assert backend.create_management_space("app-code", "App", ["someone"]) == 7


class TestCapabilityNotSupported:
    @pytest.mark.parametrize(
        ("method", "args", "capability"),
        [
            ("grant_user_group_policies", ("app-code", "App", []), "grant policies to existing user groups"),
            ("revoke_user_group_policies", (1, [AppAction.VIEW_BASIC_INFO]), "revoke user group policies"),
            (
                "grant_user_group_policies_in_bk_monitor",
                ("-1", "App", []),
                "grant policies to existing user groups (bk_monitor)",
            ),
            (
                "grant_user_group_policies_in_bk_log",
                ("-1", "App", []),
                "grant policies to existing user groups (bk_log)",
            ),
        ],
    )
    def test_missing_user_group_capabilities(self, backend, method, args, capability):
        with pytest.raises(BKIAMCapabilityNotSupportedError) as exc_info:
            getattr(backend, method)(*args)

        assert exc_info.value.capability == capability
        assert "V4 暂未提供该能力" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("method", "args"),
        [
            ("delete_management_space", (1,)),
            ("add_management_space_members", (1, ["user-0"])),
            ("delete_management_space_members", (1, ["user-0"])),
            ("update_management_space_scopes", (1, "app-code", "App", "-100")),
            ("delete_user_groups", ([1, 2],)),
        ],
    )
    def test_missing_apis_only_log(self, backend, method, args, caplog):
        """这些能力挂在应用创建/删除、成员变更主流程上，缺接口时只记错误日志，不能打断主流程"""
        getattr(backend, method)(*args)

        assert "does not support" in caplog.text


class TestResolveV4BkSpaceId:
    def test_v3_skips_monitor_space(self, settings):
        from paasng.platform.applications.helpers import _resolve_v4_bk_space_id

        settings.BK_IAM_VERSION = "v3"
        assert _resolve_v4_bk_space_id(mock.Mock(code="app-code")) is None

    def test_v4_returns_monitor_space_id(self, settings):
        from paasng.platform.applications.helpers import _resolve_v4_bk_space_id

        settings.BK_IAM_VERSION = "v4"
        space = mock.Mock(iam_resource_id="-100")
        with mock.patch(
            "paasng.platform.applications.helpers.get_or_create_bk_monitor_space",
            return_value=(space, True),
        ) as mocked:
            assert _resolve_v4_bk_space_id(mock.Mock(code="app-code")) == "-100"
            mocked.assert_called_once()


class TestCreateBuiltinUserGroups:
    def test_creates_three_groups_with_permissions_and_admin_members(self, backend, mocker, settings):
        settings.ADMIN_USERNAME = "admin"
        calls: List[Dict[str, Any]] = []

        def fake_call(operation, **kwargs):
            calls.append({"operation": operation, **kwargs})
            return {"data": {"id": 10 + len(calls)}}

        mocker.patch.object(backend, "call", side_effect=fake_call)

        groups = backend.create_builtin_user_groups(7, "app-code", app_name="App", init_members=["alice", "admin"])

        assert [group.role for group in groups] == [int(role) for role in APP_DEFAULT_ROLES]
        assert [group.id for group in groups] == [11, 12, 13]
        assert len(calls) == 3
        assert all(call["for_write"] is True for call in calls)

        admin_payload, dev_payload, ops_payload = [call["data"] for call in calls]
        assert admin_payload["members"] == [{"id": "alice", "type": "user"}]
        assert dev_payload["members"] == []
        assert ops_payload["members"] == []

        assert admin_payload["permissions"][0]["id"] == str(AppRole.ADMINISTRATOR)
        assert dev_payload["permissions"][0]["id"] == str(AppRole.DEVELOPER)
        assert ops_payload["permissions"][0]["id"] == str(AppRole.OPERATOR)

        # 开发者角色对应 8 项操作，由模型注册的角色承载，创建用户组时只提交角色 ID
        assert len(AppRole.get_actions(AppRole.DEVELOPER)) == 8
        assert dev_payload["permissions"][0]["resources"][0]["instances"] == [
            {"id": "app-code", "type": "application"}
        ]

        expired_at = admin_payload["permission_expired_at"]
        now = int(time.time())
        assert now < expired_at <= now + V4_MAX_PERMISSION_DAYS * ONE_DAY_SECONDS

    def test_conflict_reuses_existing_group_id(self, backend, mocker):
        mocker.patch.object(
            backend, "call", side_effect=BKIAMApiHTTPError("conflict", status_code=409, request_id="req-conflict")
        )
        existing = [
            {"id": 99, "name": _group_name("app-code", ApplicationRole.ADMINISTRATOR)},
            {"id": 100, "name": _group_name("app-code", ApplicationRole.DEVELOPER)},
            {"id": 101, "name": _group_name("app-code", ApplicationRole.OPERATOR)},
        ]
        mocker.patch.object(backend, "paginate", side_effect=lambda *args, **kwargs: iter(existing))

        groups = backend.create_builtin_user_groups(7, "app-code")

        assert [group.id for group in groups] == [99, 100, 101]


class TestUserGroupMembers:
    def test_delete_members_uses_operator_override(self, backend, mocker):
        mocker.patch.object(backend, "call", return_value={})

        backend.delete_user_group_members(7, ["alice"], operator="someone-else")

        assert backend.call.call_count == 1
        assert backend.operator == "creator"
        assert backend.call.call_args.kwargs["for_write"] is True
        assert backend.call.call_args.kwargs["operator"] == "someone-else"
        assert backend.call.call_args.kwargs["data"] == {"members": [{"id": "alice", "type": "user"}]}

    def test_skips_platform_admin_username(self, backend, mocker, settings):
        settings.ADMIN_USERNAME = "admin"
        mocker.patch.object(backend, "call", return_value={"data": None})

        backend.add_user_group_members(7, ["admin"], NEVER_EXPIRE_DAYS)

        backend.call.assert_not_called()


class TestFetchUserGroupMembers:
    def test_returns_only_user_members(self, backend, mocker):
        mocker.patch.object(
            backend,
            "paginate",
            return_value=iter(
                [
                    {"id": "alice", "type": "user"},
                    {"id": "dept1", "type": "department"},
                    {"id": "bob", "type": "user"},
                ]
            ),
        )

        assert backend.fetch_user_group_members(7) == ["alice", "bob"]
