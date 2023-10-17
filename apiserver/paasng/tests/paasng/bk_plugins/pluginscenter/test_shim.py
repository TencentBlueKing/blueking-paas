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
from blue_krill.web.std_error import APIError

from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.bk_plugins.pluginscenter.shim import init_plugin_in_view
from paasng.bk_plugins.pluginscenter.sourcectl import PluginRepoInitializer

pytestmark = pytest.mark.django_db


class SentinelException(Exception):
    ...


def set_plugin_repository(repository: str):
    def side_effect(plugin: PluginInstance):
        plugin.repository = repository
        plugin.save()

    return side_effect


class TestInitPlugin:
    @pytest.fixture
    def plugin(self, plugin):
        # 清空 plugin.repository
        plugin.repository = ""
        plugin.save()
        return plugin

    @pytest.fixture
    def plugin_repo_initializer(self):
        with mock.patch(
            "paasng.bk_plugins.pluginscenter.shim.get_plugin_repo_initializer", spec=PluginRepoInitializer
        ) as mocked:
            yield mocked()

    @pytest.fixture
    def mocked_create_instance(self):
        with mock.patch("paasng.bk_plugins.pluginscenter.shim.create_instance") as mocked:
            yield mocked

    def test_create_repo_failed(self, plugin, plugin_repo_initializer):
        """测试创建仓库失败的情景"""
        plugin_repo_initializer.create_project.side_effect = SentinelException
        with pytest.raises(SentinelException):
            init_plugin_in_view(plugin, "")
        assert not plugin_repo_initializer.delete_project.called

    def test_initial_repo_failed(self, plugin, plugin_repo_initializer):
        """测试初始化仓库失败的情景"""
        plugin_repo_initializer.create_project.side_effect = set_plugin_repository("foo")
        plugin_repo_initializer.initial_repo.side_effect = SentinelException
        with pytest.raises(SentinelException):
            init_plugin_in_view(plugin, "")
        assert plugin.repository == "foo"
        assert plugin_repo_initializer.delete_project.called

    def test_thirdparty_exception(self, plugin, plugin_repo_initializer, mocked_create_instance):
        """测试调用第三方系统接口异常的情景"""
        plugin_repo_initializer.create_project.side_effect = set_plugin_repository("foo")
        mocked_create_instance.side_effect = SentinelException
        with mock.patch("paasng.bk_plugins.pluginscenter.shim.add_repo_member"), pytest.raises(APIError):
            init_plugin_in_view(plugin, "")
        assert plugin.repository == "foo"
        assert plugin_repo_initializer.delete_project.called

    def test_iam_exception(self, plugin, plugin_repo_initializer, mocked_create_instance):
        """测试调用 IAM 接口异常的情景"""
        plugin_repo_initializer.create_project.side_effect = set_plugin_repository("foo")
        with mock.patch("paasng.bk_plugins.pluginscenter.shim.add_repo_member"), mock.patch(
            "paasng.bk_plugins.pluginscenter.shim.setup_builtin_grade_manager", side_effect=SentinelException
        ), pytest.raises(SentinelException):
            init_plugin_in_view(plugin, "")
        assert plugin.repository == "foo"
        assert plugin_repo_initializer.delete_project.called
