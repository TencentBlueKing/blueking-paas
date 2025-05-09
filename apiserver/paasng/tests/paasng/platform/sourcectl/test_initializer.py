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
from django.test import override_settings

from paasng.platform.sourcectl.exceptions import RepoNameConflict
from paasng.platform.sourcectl.initializer import create_new_repo_and_initialized
from paasng.platform.sourcectl.models import SourceTypeSpecConfig
from paasng.platform.sourcectl.source_types import refresh_sourcectl_types

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def mock_sourcectl_type():
    class MockSourceType:
        initializer_class = None

    return MockSourceType()


@pytest.fixture(autouse=True)
def _setup_sourcectl_types(dummy_svn_spec, dummy_gitlab_spec):
    spec_cls_module_path = "paasng.platform.sourcectl.type_specs"

    configs = [
        SourceTypeSpecConfig(
            name="tc_git",
            label_zh_cn="tc_git",
            label_en="tc_git",
            enabled=True,
            spec_cls=f"{spec_cls_module_path}.BareGitSourceTypeSpec",
        ),
    ]

    type_configs = [dummy_gitlab_spec, dummy_svn_spec]
    type_configs.extend([c.to_dict() for c in configs])
    refresh_sourcectl_types(type_configs)


class TestCreateNewRepoAndInitialized:
    COMMON_SETTINGS = override_settings(
        APP_REPO_CONF={"private_token": "test-token", "api_url": "http://api.example.com"},
        APP_REPOSITORY_GROUP="http://git.example.com/groups/test",
    )

    @patch("paasng.platform.sourcectl.initializer.get_sourcectl_type")
    def test_no_initializer_class_raise_error(self, mock_get_type, bk_module, mock_sourcectl_type):
        """没有设置 initializer_class 时抛出异常"""
        mock_sourcectl_type.initializer_class = None
        mock_get_type.return_value = mock_sourcectl_type

        with pytest.raises(NotImplementedError):
            create_new_repo_and_initialized(bk_module, "invalid_type", "test-operator")

    @pytest.mark.usefixtures("_init_tmpls")
    @COMMON_SETTINGS
    @patch("paasng.platform.sourcectl.initializer.get_sourcectl_type")
    @patch("paasng.platform.sourcectl.initializer.TcGitRepoInitializer")
    def test_template_not_exist(self, mock_initializer_cls, mock_get_type, bk_module):
        """测试模板不存在的情况"""
        mock_get_type.return_value = Mock(initializer_class=mock_initializer_cls)

        # 设置不存在的模板名称
        bk_module.source_init_template = "non_exist_template"
        bk_module.save()

        with pytest.raises(ValueError, match="Template non_exist_template does not exist"):
            create_new_repo_and_initialized(bk_module, "tc_git", "test-operator")

    @pytest.mark.usefixtures("_init_tmpls")
    @COMMON_SETTINGS
    @patch("paasng.platform.sourcectl.initializer.get_sourcectl_type")
    @patch("paasng.platform.sourcectl.initializer.TcGitRepoInitializer")
    @patch("paasng.platform.sourcectl.connector.get_repo_connector")
    def test_repo_rollback_on_error(self, mock_connector, mock_initializer_cls, mock_get_type, bk_module):
        """测试初始化失败时的回滚逻辑"""
        mock_initializer = mock_initializer_cls.return_value
        mock_initializer.create_project.return_value = Mock(repo_url="http://repo.example.com/test-repo")
        mock_initializer.initial_repo.side_effect = Exception("Init error")
        mock_get_type.return_value = Mock(initializer_class=mock_initializer_cls)
        mock_connector.return_value = Mock()

        with pytest.raises(Exception, match=r"Init error"):
            create_new_repo_and_initialized(bk_module, "tc_git", "test-operator")

        # 验证回滚操作
        mock_initializer.delete_project.assert_called_once_with("http://repo.example.com/test-repo")

    @pytest.mark.usefixtures("_init_tmpls")
    @COMMON_SETTINGS
    @patch("paasng.platform.sourcectl.initializer.get_sourcectl_type")
    @patch("paasng.platform.sourcectl.initializer.TcGitRepoInitializer")
    def test_repo_creation_conflict(self, mock_initializer_cls, mock_get_type, bk_module):
        """测试仓库名称冲突的情况"""
        mock_initializer = mock_initializer_cls.return_value
        mock_initializer.create_project.side_effect = RepoNameConflict("Path has already been taken")
        mock_get_type.return_value = Mock(initializer_class=mock_initializer_cls)

        with pytest.raises(RepoNameConflict, match="Path has already been taken"):
            create_new_repo_and_initialized(bk_module, "tc_git", "test-operator")
