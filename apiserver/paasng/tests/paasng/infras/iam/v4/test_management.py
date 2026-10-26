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
from paasng.infras.iam.base.dto import UserGroup
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


def _observability_scopes(scopes: List[Dict]) -> Dict[str, Dict]:
    return {item["system_id"]: item for item in scopes if "system_id" in item}


class TestCreateManagementSpace:
    def test_writes_paas_and_observability_scopes(self, backend):
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
        assert {item["id"] for item in scopes if "system_id" not in item} == {str(role) for role in AppRole}
        observability = _observability_scopes(scopes)
        assert set(observability) == {BK_MONITOR_SYSTEM_ID, BK_LOG_SYSTEM_ID}
        for item in observability.values():
            assert item["id"] == SPACE_OPERATOR_ROLE_ID
            assert all(res["instances"] == [{"id": "-100", "type": "space"}] for res in item["resources"])

    def test_writes_all_init_members(self, backend):
        backend.call = mock.Mock(return_value={"data": {"id": 1}})  # type: ignore

        backend.create_management_space("app-code", "App", ["alice", "bob"])

        assert backend.call.call_args.kwargs["data"]["managers"] == ["alice", "bob"]

    def test_without_bk_space_id_only_writes_paas(self, backend):
        backend.call = mock.Mock(return_value={"data": {"id": 1}})  # type: ignore

        backend.create_management_space("app-code", "App", ["someone"])

        scopes = backend.call.call_args.kwargs["data"]["permission_scope"]
        assert all("system_id" not in item for item in scopes)
        assert {item["id"] for item in scopes} == {str(role) for role in AppRole}

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
    def test_revoke_user_group_policies(self, backend):
        with pytest.raises(BKIAMCapabilityNotSupportedError) as exc_info:
            backend.revoke_user_group_policies(1, [AppAction.VIEW_BASIC_INFO])

        assert exc_info.value.capability == "revoke user group policies"
        assert "V4 暂未提供该能力" in str(exc_info.value)


class TestUpdateSpaceScopes:
    def test_overrides_with_paas_and_observability_scopes(self, backend, mocker):
        mocker.patch.object(backend, "call", return_value={})

        backend.update_management_space_scopes(42, "app-code", "App", "-100", operator="alice")

        backend.call.assert_called_once()
        assert backend.call.call_args.args[0].name == "update_space_permission_scope"
        kwargs = backend.call.call_args.kwargs
        assert kwargs["path_params"] == {"system_id": "bk_paas3", "space_id": 42}
        assert kwargs["for_write"] is True
        assert kwargs["operator"] == "alice"

        # 请求体直接是权限范围数组
        scopes = kwargs["data"]
        assert isinstance(scopes, list)
        assert {item["id"] for item in scopes if "system_id" not in item} == {str(role) for role in AppRole}
        assert set(_observability_scopes(scopes)) == {BK_MONITOR_SYSTEM_ID, BK_LOG_SYSTEM_ID}


class TestGrantGroupPermissions:
    @pytest.fixture()
    def groups(self) -> List[UserGroup]:
        return [
            UserGroup(id=group_id, name=_group_name("app-code", role), role=role)
            for group_id, role in enumerate(APP_DEFAULT_ROLES, start=11)
        ]

    @pytest.mark.parametrize(
        ("method", "system_id", "related_types"),
        [
            (
                "grant_user_group_policies_in_bk_monitor",
                BK_MONITOR_SYSTEM_ID,
                ["space", "apm_application", "rum_application", "grafana_dashboard"],
            ),
            (
                "grant_user_group_policies_in_bk_log",
                BK_LOG_SYSTEM_ID,
                ["space", "collection", "es_source", "indices"],
            ),
        ],
    )
    def test_grant_observability_role_to_each_group(self, backend, mocker, groups, method, system_id, related_types):
        mocker.patch.object(backend, "call", return_value={})

        getattr(backend, method)("-100", "App", groups)

        calls = backend.call.call_args_list
        assert [call.args[0].name for call in calls] == ["create_group_permission"] * 3
        assert [call.kwargs["path_params"] for call in calls] == [
            {"system_id": "bk_paas3", "group_id": group_id} for group_id in [11, 12, 13]
        ]
        for call in calls:
            assert call.kwargs["for_write"] is True
            [permission] = call.kwargs["data"]["permissions"]
            assert permission["id"] == SPACE_OPERATOR_ROLE_ID
            assert permission["system_id"] == system_id
            # 各关联资源类型的资源范围均为应用对应的监控空间
            assert permission["resources"] == [
                {
                    "related_resource_type_id": related_type,
                    "is_any": False,
                    "instances": [{"id": "-100", "type": "space"}],
                }
                for related_type in related_types
            ]

    def test_grant_paas_role_by_group_role(self, backend, mocker, groups):
        mocker.patch.object(backend, "call", return_value={})

        backend.grant_user_group_policies("app-code", "App", groups)

        granted = [call.kwargs["data"]["permissions"][0] for call in backend.call.call_args_list]
        assert [item["id"] for item in granted] == [
            str(utils.APPLICATION_ROLE_TO_APP_ROLE[role]) for role in APP_DEFAULT_ROLES
        ]
        assert all("system_id" not in item for item in granted)

    def test_conflict_treated_as_granted(self, backend, mocker, groups):
        mocker.patch.object(
            backend,
            "call",
            side_effect=BKIAMApiHTTPError("exists", status_code=HTTPStatus.CONFLICT, request_id="req-409"),
        )

        backend.grant_user_group_policies_in_bk_monitor("-100", "App", groups)

        assert backend.call.call_count == 3

    def test_other_errors_raised(self, backend, mocker, groups):
        mocker.patch.object(
            backend,
            "call",
            side_effect=BKIAMApiHTTPError("bad", status_code=HTTPStatus.BAD_REQUEST, request_id="req-400"),
        )

        with pytest.raises(BKIAMApiHTTPError):
            backend.grant_user_group_policies_in_bk_log("-100", "App", groups)


class TestDeleteResources:
    def test_delete_management_space(self, backend, mocker):
        mocker.patch.object(backend, "call", return_value={})

        backend.delete_management_space(42)

        backend.call.assert_called_once()
        assert backend.call.call_args.args[0].name == "delete_space"
        assert backend.call.call_args.kwargs["path_params"] == {"system_id": "bk_paas3", "space_id": 42}
        assert backend.call.call_args.kwargs["for_write"] is True

    def test_delete_user_groups_one_by_one(self, backend, mocker):
        mocker.patch.object(backend, "call", return_value={})

        backend.delete_user_groups([1, 2])

        assert [call.args[0].name for call in backend.call.call_args_list] == ["delete_group", "delete_group"]
        assert [call.kwargs["path_params"] for call in backend.call.call_args_list] == [
            {"system_id": "bk_paas3", "group_id": 1},
            {"system_id": "bk_paas3", "group_id": 2},
        ]
        assert all(call.kwargs["for_write"] is True for call in backend.call.call_args_list)

    @pytest.mark.parametrize(
        ("method", "args"),
        [("delete_management_space", (42,)), ("delete_user_groups", ([1, 2],))],
    )
    def test_not_found_is_treated_as_deleted(self, backend, mocker, method, args):
        """应用删除可能重跑，已被删除的资源不能让清理失败"""
        mocker.patch.object(
            backend, "call", side_effect=BKIAMApiHTTPError("not found", status_code=HTTPStatus.NOT_FOUND)
        )

        getattr(backend, method)(*args)

    @pytest.mark.parametrize(
        ("method", "args"),
        [("delete_management_space", (42,)), ("delete_user_groups", ([1, 2],))],
    )
    def test_other_errors_are_raised(self, backend, mocker, method, args):
        mocker.patch.object(
            backend,
            "call",
            side_effect=BKIAMApiHTTPError("boom", status_code=HTTPStatus.INTERNAL_SERVER_ERROR),
        )

        with pytest.raises(BKIAMApiHTTPError):
            getattr(backend, method)(*args)


class TestManagementSpaceMembers:
    def test_add_members(self, backend, mocker, settings):
        settings.ADMIN_USERNAME = "admin"
        mocker.patch.object(backend, "call", return_value={})

        backend.add_management_space_members(42, ["alice", "admin", "bob"], operator="someone-else")

        backend.call.assert_called_once()
        assert backend.call.call_args.args[0].name == "add_space_manager"
        kwargs = backend.call.call_args.kwargs
        assert kwargs["path_params"] == {"system_id": "bk_paas3", "space_id": 42}
        assert kwargs["data"] == {"usernames": ["alice", "bob"]}
        assert kwargs["for_write"] is True
        assert kwargs["operator"] == "someone-else"

    def test_add_only_platform_admin_skips_request(self, backend, mocker, settings):
        settings.ADMIN_USERNAME = "admin"
        mocker.patch.object(backend, "call", return_value={})

        backend.add_management_space_members(42, ["admin"])

        backend.call.assert_not_called()

    def test_delete_members(self, backend, mocker):
        mocker.patch.object(backend, "call", return_value={})

        backend.delete_management_space_members(42, ["alice", "carol"], operator="someone-else")

        backend.call.assert_called_once()
        assert backend.call.call_args.args[0].name == "delete_space_manager"
        kwargs = backend.call.call_args.kwargs
        assert kwargs["path_params"] == {"system_id": "bk_paas3", "space_id": 42}
        assert kwargs["params"] == {"usernames": "alice,carol"}
        assert kwargs["for_write"] is True
        assert kwargs["operator"] == "someone-else"

    def test_delete_empty_skips_request(self, backend, mocker):
        mocker.patch.object(backend, "call", return_value={})

        backend.delete_management_space_members(42, [])

        backend.call.assert_not_called()


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
