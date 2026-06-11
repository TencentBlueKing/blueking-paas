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

from unittest.mock import MagicMock, patch

import pytest
from svc_mysql.vendor.provider import Provider


@pytest.fixture
def mysql_mocks():
    """Mock 外部依赖，返回 (authorizer_mock, engine_mock)"""
    with (
        patch("svc_mysql.vendor.provider.gen_unique_id", return_value="test-db"),
        patch("svc_mysql.vendor.provider.generate_mysql_password", return_value="P@ssW0rd!"),
        patch("svc_mysql.vendor.provider.MySQLAuthorizer") as mock_auth_cls,
        patch("svc_mysql.vendor.provider.MySQLEngine") as mock_eng_cls,
    ):
        mock_authorizer = MagicMock()
        mock_engine = MagicMock()
        mock_auth_cls.return_value = mock_authorizer
        mock_eng_cls.return_value = mock_engine
        yield mock_authorizer, mock_engine


def make_provider(**kwargs):
    defaults = {"host": "10.0.0.1", "port": 3306, "user": "root", "password": "pwd"}
    defaults.update(kwargs)
    return Provider(**defaults)


class TestCreateCharsetDetection:
    """create() 集成测试: 验证最终建库 SQL"""

    def test_utf8mb4_sql_generated(self, mysql_mocks):
        mock_authorizer, mock_engine = mysql_mocks
        mock_authorizer.execute.return_value = [("utf8mb4", "utf8mb4_general_ci")]

        make_provider().create({"engine_app_name": "test-app"})

        create_sql = mock_engine.execute.call_args_list[0][0][0]
        assert "utf8mb4" in create_sql
        assert "utf8mb4_general_ci" in create_sql

    def test_fallback_to_utf8(self, mysql_mocks):
        mock_authorizer, mock_engine = mysql_mocks
        mock_authorizer.execute.return_value = []

        make_provider().create({"engine_app_name": "test-app"})

        create_sql = mock_engine.execute.call_args_list[0][0][0]
        assert "utf8" in create_sql
        assert "utf8mb4" not in create_sql

    def test_exception_still_creates_db(self, mysql_mocks):
        mock_authorizer, mock_engine = mysql_mocks
        mock_authorizer.execute.side_effect = Exception("Connection timed out")

        result = make_provider().create({"engine_app_name": "test-app"})

        assert result.credentials["name"] == "test-db"
        create_sql = mock_engine.execute.call_args_list[0][0][0]
        assert "utf8" in create_sql

    def test_external_template_skips_detection(self, mysql_mocks):
        mock_authorizer, mock_engine = mysql_mocks

        provider = make_provider()
        provider.db_operator_template["CREATE_DATABASE"] = "CREATE DATABASE IF NOT EXISTS `{engine.name}`;"
        provider.create({"engine_app_name": "test-app"})

        mock_authorizer.execute.assert_not_called()
