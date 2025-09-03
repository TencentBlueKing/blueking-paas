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

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim import PluginMember, Role
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


class TestSyncMembersApi:
    """成员同步接口测试"""

    @pytest.mark.usefixtures("_mock_shim_apis", "mock_members_api")
    def test_add_new_members(self, sys_api_client, pd, plugin, mock_members_api):
        """测试新增用户到空列表"""
        url = reverse(
            "sys.api.plugins_center.bk_plugins.sync_members", kwargs={"pd_id": pd.identifier, "plugin_id": plugin.id}
        )

        # 配置mock
        mock_members_api["fetch_plugin_members"].return_value = []
        remove_mock = mock_members_api["remove_user_all_roles"]
        add_mock = mock_members_api["add_role_members"]
        delete_mock = mock_members_api["delete_role_members"]

        # 发送请求
        response = sys_api_client.post(url, data=[{"username": "user1", "role": {"id": 2}}])
        assert response.status_code == 200

        # 验证调用
        remove_mock.assert_not_called()
        add_mock.assert_called_once_with(plugin, role=PluginRole.ADMINISTRATOR, usernames=["user1"])
        delete_mock.assert_not_called()

    @pytest.mark.usefixtures("_mock_shim_apis", "mock_members_api")
    def test_remove_redundant_members(self, sys_api_client, pd, plugin, mock_members_api):
        """测试删除冗余用户"""
        url = reverse(
            "sys.api.plugins_center.bk_plugins.sync_members", kwargs={"pd_id": pd.identifier, "plugin_id": plugin.id}
        )

        # 配置mock
        mock_members_api["fetch_plugin_members"].return_value = [
            PluginMember(username="old_user", role=Role(id=PluginRole.ADMINISTRATOR, name="管理员"))
        ]
        remove_mock = mock_members_api["remove_user_all_roles"]
        add_mock = mock_members_api["add_role_members"]
        delete_mock = mock_members_api["delete_role_members"]

        # 发送请求
        response = sys_api_client.post(url, data=[])
        assert response.status_code == 200

        # 验证调用
        remove_mock.assert_called_once_with(plugin, usernames=["old_user"])
        add_mock.assert_not_called()
        delete_mock.assert_not_called()

    @pytest.mark.usefixtures("_mock_shim_apis", "mock_members_api")
    def test_update_roles(self, sys_api_client, pd, plugin, mock_members_api):
        """测试角色更新场景"""
        url = reverse(
            "sys.api.plugins_center.bk_plugins.sync_members", kwargs={"pd_id": pd.identifier, "plugin_id": plugin.id}
        )

        # 配置mock
        mock_members_api["fetch_plugin_members"].return_value = [
            PluginMember(username="user1", role=Role(id=PluginRole.DEVELOPER, name="开发者"))
        ]
        remove_mock = mock_members_api["remove_user_all_roles"]
        add_mock = mock_members_api["add_role_members"]
        delete_mock = mock_members_api["delete_role_members"]

        # 发送请求
        response = sys_api_client.post(url, data=[{"username": "user1", "role": {"id": 2}}])
        assert response.status_code == 200

        # 验证调用
        remove_mock.assert_not_called()
        add_mock.assert_called_once_with(plugin, role=PluginRole.ADMINISTRATOR, usernames=["user1"])
        delete_mock.assert_any_call(plugin, role=PluginRole.DEVELOPER, usernames=["user1"])

    @pytest.mark.usefixtures("_mock_shim_apis", "mock_members_api")
    def test_mixed_operations(self, sys_api_client, pd, plugin, mock_members_api):
        """测试混合操作场景"""
        url = reverse(
            "sys.api.plugins_center.bk_plugins.sync_members", kwargs={"pd_id": pd.identifier, "plugin_id": plugin.id}
        )

        # 配置mock
        mock_members_api["fetch_plugin_members"].return_value = [
            PluginMember(username="user1", role=Role(id=PluginRole.ADMINISTRATOR, name="管理员")),
            PluginMember(username="user2", role=Role(id=PluginRole.DEVELOPER, name="开发者")),
        ]
        remove_mock = mock_members_api["remove_user_all_roles"]
        add_mock = mock_members_api["add_role_members"]
        delete_mock = mock_members_api["delete_role_members"]

        # 发送请求
        request_data = [{"username": "user1", "role": {"id": 3}}, {"username": "user3", "role": {"id": 3}}]
        response = sys_api_client.post(url, data=request_data)
        assert response.status_code == 200

        # 验证调用
        remove_mock.assert_called_once_with(plugin, usernames=["user2"])
        assert add_mock.call_args_list == [
            mock.call(plugin, role=PluginRole.DEVELOPER, usernames=["user1", "user3"]),
        ]
        delete_mock.assert_called_once_with(plugin, role=PluginRole.ADMINISTRATOR, usernames=["user1"])
