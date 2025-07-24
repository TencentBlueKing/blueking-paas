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
from tests.utils.mocks.services import (
    create_local_mysql_service,
    create_local_rabbitmq_service,
    provision_with_credentials,
)

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetEnvVarsSelectedAddons:
    @pytest.fixture(autouse=True)
    def _setup_services(self, bk_module):
        """设置增强服务并绑定到模块"""
        mysql_service = create_local_mysql_service()
        rabbitmq_service = create_local_rabbitmq_service()

        provision_with_credentials(
            bk_module, mysql_service, credentials={"MYSQL_HOST": "mysql.com", "MYSQL_PORT": "3306"}
        )

        provision_with_credentials(bk_module, rabbitmq_service, credentials={"MQ_URL": "mq.com"})

        base_vars = {"DB_HOST": "db.com", "APP_ENV": "prod"}
        with mock.patch("paasng.accessories.dev_sandbox.config_var.UnifiedEnvVarsReader") as mock_reader:
            mock_reader.return_value.get_kv_map.return_value = base_vars
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
        # 获取实际的服务名称
        mysql_service_name = "MySQL"
        rabbitmq_service_name = "rabbitmq"

        # 测试服务全选的情况
        selected_services = [mysql_service_name, rabbitmq_service_name]
        result = list_vars_builtin_addons_custom(bk_stag_env, selected_services)

        assert result == {"MYSQL_HOST": "mysql.com", "MYSQL_PORT": "3306", "MQ_URL": "mq.com"}

        # 测试仅选择一个服务的情况
        selected_services = [mysql_service_name]
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
        mysql_service_name = "MySQL"
        rabbitmq_service_name = "rabbitmq"

        selected_services = [mysql_service_name, rabbitmq_service_name]
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
        with mock.patch("paasng.accessories.dev_sandbox.config_var.UnifiedEnvVarsReader") as mock_reader:
            mock_reader.return_value.get_kv_map.return_value = {
                "DB_HOST": "db.com",
                "APP_ENV": "prod",
                "MYSQL_HOST": "old-mysql.com",
            }

            result = get_env_vars_selected_addons(bk_stag_env, None)

            # 验证 MYSQL_HOST 被覆盖
            assert result["MYSQL_HOST"] == "mysql.com"
            assert result["DB_HOST"] == "db.com"
