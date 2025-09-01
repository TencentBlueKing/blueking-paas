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
import string
from unittest import mock

import pytest
from rest_framework.reverse import reverse

from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.fixture
def _mock_shim_apis():
    with (
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.setup_builtin_grade_manager"),
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.setup_builtin_user_groups"),
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.add_role_members"),
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.create_instance"),
    ):
        yield


@pytest.mark.parametrize(
    ("data", "status_code", "error_msg"),
    [
        (
            {
                "id": generate_random_string(length=10, chars=string.ascii_lowercase),
                "name": generate_random_string(length=20, chars=string.ascii_lowercase),
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
            },
            201,
            "",
        ),
        (
            {
                "id": generate_random_string(length=10, chars=string.ascii_lowercase),
                "name": generate_random_string(length=20, chars=string.ascii_lowercase),
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
                "extra_fields": {"email": "foo@example.com", "distributor_codes": ["1", "2"]},
            },
            201,
            "",
        ),
        (
            {
                "id": "invalid_id",
                "name": "2",
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
            },
            400,
            "id: 输入值不匹配要求的模式",
        ),
        # 插件 ID 冲突测试用例
        (
            {
                "id": "duplicate_id",
                "name": generate_random_string(length=20, chars=string.ascii_lowercase),
                "template": "foo",
                "creator": "user1",
                "repository": "http://git.example.com/template.git",
            },
            400,
            "插件已存在",
        ),
    ],
)
@pytest.mark.usefixtures("_mock_shim_apis")
def test_create_api(sys_api_client, pd, plugin, data, status_code, error_msg):
    url = reverse("sys.api.plugins_center.bk_plugins.create", kwargs={"pd_id": pd.identifier})
    with (
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.setup_builtin_grade_manager"),
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.setup_builtin_user_groups"),
        mock.patch("paasng.bk_plugins.pluginscenter.sys_apis.views.shim.add_role_members"),
    ):
        if data["id"] == "duplicate_id":
            data["id"] = plugin.id

        response = sys_api_client.post(url, data=data)
        assert response.status_code == status_code
        if status_code == 201:
            assert response.data["publisher"] == data["creator"]
            assert response.data["repository"] == data["repository"]

        if error_msg:
            assert error_msg in response.json()["detail"]


@pytest.fixture
def mock_members_api():
    with mock.patch.multiple(
        "paasng.bk_plugins.pluginscenter.sys_apis.views.members_api",
        fetch_plugin_members=mock.DEFAULT,
        remove_user_all_roles=mock.DEFAULT,
        add_role_members=mock.DEFAULT,
        delete_role_members=mock.DEFAULT,
    ) as mocks:
        yield mocks


@pytest.mark.parametrize(
    ("existing_members", "request_data", "expected_remove", "expected_add", "expected_delete"),
    [
        # 新增用户
        (
            [],  # 初始无成员
            [{"username": "user1", "role": {"id": 2}}],  # 管理员角色ID为2
            [],  # 需要删除的冗余用户
            [(2, ["user1"])],  # 需要添加的权限
            [],  # 需要删除的权限
        ),
        # 删除冗余用户
        (
            [{"username": "old_user", "roles": [2]}],  # 初始成员
            [],  # 请求数据为空
            ["old_user"],  # 需要删除的冗余用户
            [],  # 需要添加的权限
            [],  # 需要删除的权限
        ),
        # 更新用户角色
        (
            [{"username": "user1", "roles": [2, 3]}],  # 初始有多个角色（2=管理员，3=开发者）
            [{"username": "user1", "role": {"id": 2}}],  # 请求只保留管理员角色
            [],  # 无冗余用户
            [(2, ["user1"])],  # 添加管理员角色（虽然已有但幂等）
            [("user1", [3])],  # 需要删除开发者角色
        ),
        # 混合场景
        (
            [
                {"username": "user1", "roles": [2]},
                {"username": "user2", "roles": [3]},
            ],
            [
                {"username": "user1", "role": {"id": 2}},
                {"username": "user3", "role": {"id": 3}},
            ],
            ["user2"],  # 需要删除user2
            [(2, ["user1"]), (3, ["user3"])],  # 需要添加user3
            [],  # 无需要删除的角色
        ),
    ],
)
@pytest.mark.usefixtures("_mock_shim_apis", "mock_members_api")
def test_sync_members(
    sys_api_client,
    pd,
    plugin,
    mock_members_api,
    existing_members,
    request_data,
    expected_remove,
    expected_add,
    expected_delete,
):
    """测试成员同步功能"""
    url = reverse(
        "sys.api.plugins_center.bk_plugins.sync_members", kwargs={"pd_id": pd.identifier, "plugin_id": plugin.id}
    )

    # Mock成员API返回
    mock_members_api["fetch_plugin_members"].return_value = existing_members
    remove_mock = mock_members_api["remove_user_all_roles"]
    add_mock = mock_members_api["add_role_members"]
    delete_mock = mock_members_api["delete_role_members"]

    # 发送请求
    response = sys_api_client.post(url, data=request_data)
    if response.status_code == 400:
        breakpoint()
    assert response.status_code == 200

    # 验证删除冗余用户
    if expected_remove:
        remove_mock.assert_called_once_with(plugin=plugin, usernames=expected_remove)
    else:
        remove_mock.assert_not_called()

    # 验证添加角色
    for role, users in expected_add:
        assert mock.call(plugin, role=role, usernames=users) in add_mock.call_args_list

    # 验证删除角色
    for username, roles in expected_delete:
        for role in roles:
            delete_mock.assert_any_call(plugin, role=role, usernames=[username])
