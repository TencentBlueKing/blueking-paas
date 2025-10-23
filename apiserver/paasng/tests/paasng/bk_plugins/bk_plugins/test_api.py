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
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status

from paasng.core.tenant.constants import AppTenantMode
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.fixture
def valid_plugin_data():
    """有效的插件创建数据"""
    return {
        "id": generate_random_string(length=8, chars="abcdefghijklm"),
        "name_zh_cn": "测试插件",
        "name_en": "Test Plugin",
        "template": {
            "id": "python-template",
            "name": "Python模板",
            "language": "Python",
            "applicable_language": None,
            "repository": "https://github.com/example/template.git",
        },
        "extra_fields": {"email": "test@example.com", "distributor_codes": ["1", "2"]},
        "repository": "https://git.example.com/test-plugin.git",
        "operator": "test_user",
        "plugin_tenant_mode": AppTenantMode.GLOBAL.value,
        "plugin_tenant_id": "default",
        "tenant_id": "default",
    }


@pytest.fixture
def ai_agent_plugin_data(valid_plugin_data):
    """AI Agent 插件创建数据"""
    data = valid_plugin_data.copy()
    data["template"]["id"] = "bk-ai-python-template"
    return data


@pytest.fixture
def invalid_plugin_data():
    """无效的插件创建数据"""
    return {
        "id": "invalid_id_with_special_chars!@#",
        "name_zh_cn": "",
        "name_en": "",
        "template": {"id": "", "name": "", "language": "", "repository": ""},
        "repository": "",
        "operator": "",
        "plugin_tenant_mode": "invalid_mode",
        "plugin_tenant_id": "",
        "tenant_id": "",
    }


class TestCreatePluginAPI:
    """测试 create_plugin API 接口"""

    @pytest.fixture(autouse=True)
    def _setup_mocks(self):
        """设置必要的 mock"""
        with mock.patch(
            "paasng.bk_plugins.bk_plugins.pluginscenter_views.create_application"
        ) as mock_create_app, mock.patch(
            "paasng.bk_plugins.bk_plugins.pluginscenter_views.create_default_module"
        ) as mock_create_module, mock.patch(
            "paasng.bk_plugins.bk_plugins.pluginscenter_views.init_module_in_view"
        ) as mock_init_module, mock.patch(
            "paasng.bk_plugins.bk_plugins.pluginscenter_views.create_market_config"
        ) as mock_create_market, mock.patch(
            "paasng.bk_plugins.bk_plugins.pluginscenter_views.post_create_application.send"
        ) as mock_signal, mock.patch(
            "paasng.bk_plugins.bk_plugins.pluginscenter_views.make_bk_plugin"
        ) as mock_make_plugin:
            # 设置 mock 返回值
            mock_app = mock.MagicMock()
            mock_app.code = "test-plugin"
            mock_app.language = "Python"
            mock_app.save = mock.MagicMock()
            mock_create_app.return_value = mock_app

            mock_module = mock.MagicMock()
            mock_module.language = "Python"
            mock_create_module.return_value = mock_module

            mock_plugin_data = {"id": "test-plugin", "name": "测试插件", "language": "Python"}
            mock_make_plugin.return_value = mock_plugin_data

            self.mock_create_app = mock_create_app
            self.mock_create_module = mock_create_module
            self.mock_init_module = mock_init_module
            self.mock_create_market = mock_create_market
            self.mock_signal = mock_signal
            self.mock_make_plugin = mock_make_plugin

            yield

    def test_create_plugin_success(self, sys_api_client, valid_plugin_data):
        """测试成功创建插件"""
        url = reverse("sys.api.plugins_center.bk_plugins.create")

        response = sys_api_client.post(url, data=json.dumps(valid_plugin_data), content_type="application/json")
        assert response.status_code == status.HTTP_201_CREATED

        # 验证调用了相关方法
        self.mock_create_app.assert_called_once()
        self.mock_create_module.assert_called_once()
        self.mock_init_module.assert_called_once()
        self.mock_create_market.assert_called_once()
        self.mock_signal.assert_called_once()
        self.mock_make_plugin.assert_called_once()

    def test_create_ai_agent_plugin(self, sys_api_client, ai_agent_plugin_data):
        """测试创建 AI Agent 插件"""
        url = reverse("sys.api.plugins_center.bk_plugins.create")

        response = sys_api_client.post(url, data=json.dumps(ai_agent_plugin_data), content_type="application/json")

        assert response.status_code == status.HTTP_201_CREATED

        # 验证 create_application 被调用时 is_ai_agent_app=True
        call_args = self.mock_create_app.call_args
        assert call_args[1]["is_ai_agent_app"] is True
