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
from unittest import mock

import pytest

from paasng.bk_plugins.pluginscenter.iam_adaptor.management.client import BKIAMClient


@pytest.fixture()
def iam_management_client():
    with mock.patch(
        "paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim.lazy_iam_client", new=BKIAMClient()
    ) as mocked_client:
        stub = StubManagementClient()
        mocked_client.client = mock.MagicMock(spec=StubManagementClient)
        mocked_client.client.configure_mock(
            **{f"{attr}.side_effect": getattr(stub, attr) for attr in dir(stub) if not attr.startswith("__")}
        )
        yield mocked_client.client


class StubManagementClient:
    """Stub client implement all IAM management API"""

    def management_grade_managers(self, data):
        """See also:"""
        return {"code": 0, "message": "ok", "data": {"id": 1}}

    def management_grade_manager_members(self, path_params):
        return {"code": 0, "message": "ok", "data": ["admin", "test"]}

    def management_add_grade_manager_members(self, path_params, data):
        return {"code": 0, "message": "ok", "data": {}}

    def management_delete_grade_manager_members(self, path_params, params):
        return {"code": 0, "message": "ok", "data": {}}

    def v2_management_grade_manager_create_groups(self, path_params, data):
        return {"code": 0, "message": "ok", "data": [1, 2]}

    def v2_management_grade_manager_delete_group(self, path_params):
        return {"code": 0, "message": "ok", "data": {}}

    def v2_management_group_members(self, path_params, params):
        if path_params["group_id"] == 1:
            users = [
                {"type": "user", "id": "admin", "name": "管理员", "expired_at": 4102444800},
                {"type": "department", "id": "1", "name": "部门1", "expired_at": 4102444800},
            ]
        else:
            users = [
                {"type": "user", "id": "admin", "name": "管理员", "expired_at": 4102444800},
                {"type": "user", "id": "foo", "name": "用户1", "expired_at": 1619587562},
                {"type": "department", "id": "1", "name": "部门1", "expired_at": 4102444800},
                {"type": "user", "id": "bar", "name": "用户2", "expired_at": 1619587562},
            ]
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "count": 3,
                "results": users,
            },
        }

    def v2_management_add_group_members(self, path_params, data):
        return {"code": 0, "message": "ok", "data": {}}

    def v2_management_delete_group_members(self, path_params, params):
        return {"code": 0, "message": "ok", "data": {}}

    def v2_management_groups_policies_grant(self, path_params, data):
        return {"code": 0, "message": "ok", "data": {}}
