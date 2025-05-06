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

from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.test import override_settings

from paasng.platform.modules.utils import get_module_init_repo_context
from paasng.platform.sourcectl.constants import TencentGitMemberRole, TencentGitVisibleLevel
from paasng.platform.sourcectl.initializer import create_new_repo_and_initialized
from paasng.platform.templates.models import Template

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def mock_sourcectl_type():
    class MockSourceType:
        initializer_class = None

    return MockSourceType()


class TestCreateNewRepoAndInitialized:
    @patch("paasng.platform.sourcectl.initializer.get_sourcectl_type")
    def test_no_initializer_class_raise_error(self, mock_get_type, bk_module, mock_sourcectl_type):
        """没有设置 initializer_class 时抛出异常"""
        mock_sourcectl_type.initializer_class = None
        mock_get_type.return_value = mock_sourcectl_type

        with pytest.raises(NotImplementedError):
            create_new_repo_and_initialized(bk_module, "invalid_type", "test-operator")

    @pytest.mark.usefixtures("_init_tmpls")
    @patch("paasng.platform.sourcectl.initializer.get_sourcectl_type")
    @patch("paasng.platform.sourcectl.initializer.TcGitRepoInitializer")
    @patch("paasng.platform.modules.utils.get_module_init_repo_context")
    @override_settings(
        APP_REPO_CONF={"private_token": "test-token", "api_url": "http://api.example.com"},
        APP_REPOSITORY_GROUP="http://git.example.com/groups/test",
    )
    def test_normal_flow_with_mocks(
        self, mock_get_context, mock_initializer_cls, mock_get_type, bk_module, mock_sourcectl_type
    ):
        """测试正常流程"""
        mock_initializer = Mock()
        mock_initializer_cls.return_value = mock_initializer
        mock_sourcectl_type.initializer_class = mock_initializer_cls
        mock_get_type.return_value = mock_sourcectl_type

        # 初始化模板的上下文
        template = Template.objects.get(name="dummy_template")
        mock_context = get_module_init_repo_context(bk_module, template.type)
        mock_get_context.return_value = mock_context

        create_new_repo_and_initialized(bk_module, "tc_git", "test-operator")

        # 验证初始化器调用
        mock_initializer_cls.assert_called_once_with(
            repository_group=settings.APP_REPOSITORY_GROUP,
            api_url=settings.APP_REPO_CONF["api_url"],
            user_credentials={"private_token": "test-token"},
        )

        # 验证仓库创建
        expected_repo_name = f"{bk_module.application.code}_{bk_module.name}"
        expected_description = f"{bk_module.application.name}({bk_module.name} 模块)"
        mock_initializer.create_project.assert_called_once_with(
            expected_repo_name, TencentGitVisibleLevel.PUBLIC, expected_description
        )

        # 验证仓库初始化
        mock_initializer.initial_repo.assert_called_once_with(
            mock_initializer.create_project.return_value.repo_url, template, mock_context
        )

        # 验证成员添加
        mock_initializer.add_member.assert_called_once_with(
            mock_initializer.create_project.return_value.repo_url, "test-operator", TencentGitMemberRole.MASTER
        )
