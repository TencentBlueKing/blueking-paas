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

from unittest import mock

import pytest

from paasng.accessories.dev_sandbox.config_var import get_env_vars_selected_addons, list_vars_builtin_addons_custom

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetEnvVarsSelectedAddons:
    @pytest.fixture(autouse=True)
    def _mock_dependencies(self):
        mock_base_vars = mock.MagicMock()
        mock_base_vars.get_kv_map.return_value = {"DB_HOST": "db.com", "APP_ENV": "prod"}

        mock_service_group1 = mock.MagicMock()
        mock_service_group1.service.name = "mysql"
        mock_service_group1.data = {"MYSQL_HOST": "mysql.com", "MYSQL_PORT": "3306"}

        mock_service_group2 = mock.MagicMock()
        mock_service_group2.service.name = "rabbitmq"
        mock_service_group2.data = {"MQ_URL": "mq.com"}

        mock_service_sharing_manager = mock.MagicMock()
        mock_service_sharing_manager.return_value.get_env_variable_groups.return_value = [mock_service_group1]

        mock_mixed_service_mgr = mock.MagicMock()
        mock_mixed_service_mgr.get_env_var_groups.return_value = [mock_service_group2]

        with (
            mock.patch("paasng.accessories.dev_sandbox.config_var.UnifiedEnvVarsReader", return_value=mock_base_vars),
            mock.patch(
                "paasng.accessories.dev_sandbox.config_var.ServiceSharingManager", mock_service_sharing_manager
            ),
            mock.patch("paasng.accessories.dev_sandbox.config_var.mixed_service_mgr", mock_mixed_service_mgr),
        ):
            yield

    def test_get_env_vars_selected_addons_merge(self, bk_module, bk_stag_env):
        """测试环境变量合并"""
        result = get_env_vars_selected_addons(bk_stag_env, None)

        assert result == {
            "DB_HOST": "db.com",
            "APP_ENV": "prod",
            "MYSQL_HOST": "mysql.com",
            "MYSQL_PORT": "3306",
            "MQ_URL": "mq.com",
        }

    def test_list_vars_builtin_addons_custom_filter(self, bk_module, bk_stag_env):
        """测试根据增强服务名称过滤"""
        # 测试服务全选的情况
        selected_services = ["mysql", "rabbitmq"]
        result = list_vars_builtin_addons_custom(bk_stag_env, selected_services)

        assert result == {"MYSQL_HOST": "mysql.com", "MYSQL_PORT": "3306", "MQ_URL": "mq.com"}

        # 测试仅选择一个服务的情况
        selected_services = ["mysql"]
        result = list_vars_builtin_addons_custom(bk_stag_env, selected_services)
        assert result == {"MYSQL_HOST": "mysql.com", "MYSQL_PORT": "3306"}

        # 测试不选择服务的情况
        selected_services = []
        result = list_vars_builtin_addons_custom(bk_stag_env, selected_services)
        assert result == {}

    def test_list_vars_builtin_addons_custom_none_filter(self, bk_module, bk_stag_env):
        result = list_vars_builtin_addons_custom(bk_stag_env, None)

        assert result == {"MYSQL_HOST": "mysql.com", "MYSQL_PORT": "3306", "MQ_URL": "mq.com"}

    def test_get_env_vars_selected_addons_with_selected_services(self, bk_module, bk_stag_env):
        """测试当提供选定的服务名称时的行为"""
        selected_services = ["mysql", "rabbitmq"]
        result = get_env_vars_selected_addons(bk_stag_env, selected_services)

        assert result == {
            "DB_HOST": "db.com",
            "APP_ENV": "prod",
            "MYSQL_HOST": "mysql.com",
            "MYSQL_PORT": "3306",
            "MQ_URL": "mq.com",
        }

    def test_get_env_vars_selected_addons_override(self, bk_module, bk_stag_env):
        """测试环境变量覆盖的情况"""
        # 创建新的基础变量模拟对象，包含冲突的键
        mock_base_vars = mock.MagicMock()
        mock_base_vars.get_kv_map.return_value = {
            "DB_HOST": "db.com",
            "APP_ENV": "prod",
            "MYSQL_HOST": "old-mysql.com",
        }

        with mock.patch(
            "paasng.platform.engine.configurations.config_var.UnifiedEnvVarsReader", return_value=mock_base_vars
        ):
            result = get_env_vars_selected_addons(bk_stag_env, None)

            # 验证 MYSQL_HOST 被覆盖
            assert result["MYSQL_HOST"] == "mysql.com"
            assert result["DB_HOST"] == "db.com"

    def test_list_vars_builtin_addons_custom_no_groups(self, bk_module, bk_stag_env):
        """测试当没有变量组时的行为"""
        with mock.patch(
            "paasng.accessories.dev_sandbox.config_var.ServiceSharingManager"
        ) as mock_service_sharing_manager:
            mock_service_sharing_manager.return_value.get_env_variable_groups.return_value = []

            with mock.patch(
                "paasng.accessories.dev_sandbox.config_var.mixed_service_mgr.get_env_var_groups", return_value=[]
            ):
                result = list_vars_builtin_addons_custom(bk_stag_env, None)
                assert result == {}
