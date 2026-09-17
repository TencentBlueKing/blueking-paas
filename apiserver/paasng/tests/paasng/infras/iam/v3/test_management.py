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

from unittest import mock

import pytest

from paasng.infras.iam.base.dto import UserGroup
from paasng.infras.iam.v3.management import BKIAMV3ManagementBackend
from paasng.platform.applications.constants import ApplicationRole


@pytest.fixture()
def backend() -> BKIAMV3ManagementBackend:
    return BKIAMV3ManagementBackend("tenant-foo")


@pytest.fixture()
def mocked_v3_client(backend):
    """替换 V3 客户端，仅验证版本无关方法到 V3 方法的映射"""
    with mock.patch.object(backend, "_client") as mocked:
        yield mocked


class TestMethodMapping:
    """契约中的中立方法名须准确映射到 V3 的分级管理员/用户组接口"""

    def test_create_management_space(self, backend, mocked_v3_client):
        mocked_v3_client.create_grade_managers.return_value = 42

        assert backend.create_management_space("app-code", "App", ["admin"], bk_space_id="-1") == 42
        mocked_v3_client.create_grade_managers.assert_called_once_with("app-code", "App", ["admin"])

    def test_fetch_management_space(self, backend, mocked_v3_client):
        backend.fetch_management_space("app-code")
        mocked_v3_client.fetch_grade_manager.assert_called_once_with("app-code")

    def test_delete_management_space(self, backend, mocked_v3_client):
        backend.delete_management_space(42)
        mocked_v3_client.delete_grade_manager.assert_called_once_with(42)

    def test_management_space_members(self, backend, mocked_v3_client):
        backend.fetch_management_space_members(42)
        mocked_v3_client.fetch_grade_manager_members.assert_called_once_with(42)

        backend.add_management_space_members(42, ["user-0"])
        mocked_v3_client.add_grade_manager_members.assert_called_once_with(42, ["user-0"])

        backend.delete_management_space_members(42, ["user-0"])
        mocked_v3_client.delete_grade_manager_members.assert_called_once_with(42, ["user-0"])

    def test_update_management_space_scopes(self, backend, mocked_v3_client):
        """V4 暂缺该能力，V3 侧仍走原有的分级管理员更新接口"""
        backend.update_management_space_scopes(42, "app-code", "App", "-1")
        mocked_v3_client.update_grade_managers_with_bksaas_space.assert_called_once_with(42, "app-code", "App", "-1")

    def test_user_group_members(self, backend, mocked_v3_client):
        backend.add_user_group_members(7, ["user-0"], -1)
        mocked_v3_client.add_user_group_members.assert_called_once_with(7, ["user-0"], -1)

        backend.delete_user_group_members(7, ["user-0"])
        mocked_v3_client.delete_user_group_members.assert_called_once_with(7, ["user-0"])


class TestUserGroupDTOConversion:
    def test_create_builtin_user_groups_returns_dto(self, backend, mocked_v3_client):
        mocked_v3_client.create_builtin_user_groups.return_value = [
            {"id": 7, "name": "app-code-管理者", "description": "管理者", "role": ApplicationRole.ADMINISTRATOR},
            {"id": 8, "name": "app-code-开发者", "description": "开发者", "role": ApplicationRole.DEVELOPER},
        ]

        groups = backend.create_builtin_user_groups(42, "app-code")

        assert groups == [
            UserGroup(id=7, name="app-code-管理者", role=ApplicationRole.ADMINISTRATOR.value, description="管理者"),
            UserGroup(id=8, name="app-code-开发者", role=ApplicationRole.DEVELOPER.value, description="开发者"),
        ]

    def test_grant_policies_restores_v3_payload(self, backend, mocked_v3_client):
        groups = [UserGroup(id=7, name="app-code-管理者", role=ApplicationRole.ADMINISTRATOR.value)]

        backend.grant_user_group_policies("app-code", "App", groups)

        mocked_v3_client.grant_user_group_policies.assert_called_once_with(
            "app-code",
            "App",
            [{"id": 7, "name": "app-code-管理者", "role": ApplicationRole.ADMINISTRATOR.value}],
        )
