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


class TestTemplateNeedsCharset:
    """验证 Formatter.parse() 对占位符的精确匹配"""

    @pytest.mark.parametrize(
        ("template", "expected"),
        [
            # {charset} / {collation} 占位符 -> True
            (
                "CREATE DATABASE IF NOT EXISTS `{engine.name}` DEFAULT CHARACTER SET {charset} COLLATE {collation};",
                True,
            ),
            ("CREATE DATABASE IF NOT EXISTS `{engine.name}` COLLATE {collation};", True),
            ("CREATE DATABASE IF NOT EXISTS `{engine.name}` CHARACTER SET {charset};", True),
            # 不含占位符 -> False
            ("CREATE DATABASE IF NOT EXISTS `{engine.name}`;", False),
            ("DROP DATABASE IF EXISTS `{engine.name}`", False),
            # 字面值 charset=utf8 不是 {charset} 占位符 -> False
            ("CREATE DATABASE IF NOT EXISTS `{engine.name}` DEFAULT charset=utf8 COLLATE utf8_general_ci;", False),
        ],
    )
    def test(self, template, expected):
        assert make_provider()._template_needs_charset(template) is expected


class TestCreateCharsetDetection:
    """create() 集成测试: 验证最终建库 SQL"""

    def test_utf8mb4_sql_generated(self, mysql_mocks):
        """探测到 utf8mb4 -> 建库 SQL 含 utf8mb4 + utf8mb4_general_ci"""

        mock_authorizer, mock_engine = mysql_mocks
        mock_authorizer.execute.return_value = [("utf8mb4", "utf8mb4_general_ci")]

        make_provider().create({"engine_app_name": "test-app"})

        create_sql = mock_engine.execute.call_args_list[0][0][0]
        assert "utf8mb4" in create_sql
        assert "utf8mb4_general_ci" in create_sql

    def test_fallback_to_utf8(self, mysql_mocks):
        """utf8mb4 不可用 -> 建库 SQL 回退 utf8"""

        mock_authorizer, mock_engine = mysql_mocks
        mock_authorizer.execute.return_value = []

        make_provider().create({"engine_app_name": "test-app"})

        create_sql = mock_engine.execute.call_args_list[0][0][0]
        assert "utf8" in create_sql
        assert "utf8mb4" not in create_sql

    def test_exception_still_creates_db(self, mysql_mocks):
        """探测异常 -> 降级 utf8 且建库成功"""

        mock_authorizer, mock_engine = mysql_mocks
        mock_authorizer.execute.side_effect = Exception("Connection timed out")

        result = make_provider().create({"engine_app_name": "test-app"})

        assert result.credentials["name"] == "test-db"
        create_sql = mock_engine.execute.call_args_list[0][0][0]
        assert "utf8" in create_sql

    def test_external_template_skips_detection(self, mysql_mocks):
        """外部模板不含 {charset}/{collation} 占位符 -> 不执行探测"""
        mock_authorizer, mock_engine = mysql_mocks

        provider = make_provider()
        provider.db_operator_template["CREATE_DATABASE"] = "CREATE DATABASE IF NOT EXISTS `{engine.name}`;"
        provider.create({"engine_app_name": "test-app"})

        mock_authorizer.execute.assert_not_called()

    def test_literal_charset_template_skips_detection(self, mysql_mocks):
        """自定义模板 charset=utf8 是字面值而非占位符 -> 不探测"""

        mock_authorizer, mock_engine = mysql_mocks

        provider = make_provider()
        provider.db_operator_template["CREATE_DATABASE"] = (
            "CREATE DATABASE IF NOT EXISTS `{engine.name}` DEFAULT charset=utf8 COLLATE utf8_general_ci;"
        )
        provider.create({"engine_app_name": "test-app"})

        mock_authorizer.execute.assert_not_called()
