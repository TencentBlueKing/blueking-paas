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

import datetime
from unittest.mock import MagicMock, patch

import pytest

from paasng.platform.mgrlegacy.constants import LegacyAppTag
from paasng.platform.mgrlegacy.serializers import LegacyAppSLZ
from paasng.platform.mgrlegacy.utils import LegacyAppManager


class TestLegacyAppSLZ:
    @pytest.fixture
    def base_data(self):
        """提供测试基础数据"""
        return {
            "category": "test_category",
            "legacy_app_id": 1,
            "code": "test_app",
            "name": "测试应用",
            "logo": "http://example.com/logo.png",
            "tag": "support",
            "not_support_reasons": [],
            "language": "Python",
            "created": datetime.datetime(2023, 1, 1, 10, 0, 0),
            "latest_migration_id": 0,
            "finished_migration": False,
            "is_active": True,
            "is_prod_deployed": False,
            "has_prod_deployed_before_migration": False,
            "prod_exposed_link": "http://example.com/prod",
            "stag_exposed_link": "http://example.com/stag",
            "region": "default",
            "migration_finished_date": datetime.datetime(2023, 1, 2, 10, 0, 0),
            "legacy_url": "http://example.com/legacy",
        }

    def test_serializer(self, base_data):
        """测试序列化时只包含 Meta.fields 中定义的字段"""

        # 创建实例对象而不是直接序列化数据
        serializer = LegacyAppSLZ(base_data)

        # 使用 Meta.fields 进行序列化
        serialized_data = serializer.data

        # 验证只包含 Meta.fields 中定义的字段
        expected_fields = set(LegacyAppSLZ.Meta.fields)
        actual_fields = set(serialized_data.keys())

        # 检查实际输出的字段是否是 Meta.fields 的子集
        assert actual_fields.issubset(expected_fields), f"Found unexpected fields: {actual_fields - expected_fields}"

        # 检查 Meta.fields 中的字段是否都在输出结果中
        assert expected_fields.issubset(actual_fields), f"Missing expected fields: {expected_fields - actual_fields}"

        # 检查特定字段是否包含在输出中（在 Meta.fields 中）
        assert "code" in serialized_data
        assert "name" in serialized_data

        # 检查特定字段是否被排除在输出外（不在 Meta.fields 中）
        excluded_fields = set(base_data.keys()) - set(LegacyAppSLZ.Meta.fields)
        for field in excluded_fields:
            assert field not in serialized_data, f"Field {field} should be excluded"


class TestLegacyAppManager:
    @pytest.fixture
    def mock_legacy_app(self):
        """创建模拟的 legacy_app 对象"""
        mock_app = MagicMock()
        mock_app.id = 123
        mock_app.code = "test-app"
        mock_app.name = "测试应用"
        mock_app.language = "Python"
        mock_app.created_date = datetime.datetime(2023, 1, 1, 10, 0, 0)
        return mock_app

    @pytest.fixture
    def setup_manager(self, mock_legacy_app):
        """设置 LegacyAppManager 实例及必要的模拟"""
        with (
            patch("paasng.platform.mgrlegacy.utils.LegacyAppProxy") as mock_proxy_class,
            patch("paasng.platform.mgrlegacy.utils.MigrationProcess.objects.filter") as mock_filter,
        ):
            # 模拟 MigrationProcess 查询结果
            mock_filter.return_value.last.return_value = None

            # 配置代理模拟
            mock_proxy = MagicMock()
            mock_proxy.get_logo_url.return_value = "http://example.com/logo.png"
            mock_proxy.is_prod_deployed.return_value = False
            mock_proxy.has_prod_deployed.return_value = False
            mock_proxy.legacy_url.return_value = "http://example.com/legacy"
            mock_proxy_class.return_value = mock_proxy

            # 创建管理器实例
            mock_session = MagicMock()
            manager = LegacyAppManager(mock_legacy_app, mock_session)

            # 模拟必要的属性
            manager.app_migration_tag = (LegacyAppTag.SUPPORT.value, [])
            manager.category = "todoMigrate"

            # 使用 patch.object 来模拟方法
            with (
                patch.object(manager, "get_latest_migration_id", return_value=None),
                patch.object(manager, "is_finished_migration", return_value=False),
                patch.object(manager, "is_active", return_value=True),
                patch.object(manager, "has_prod_deployed_before_migration", return_value=False),
                patch.object(manager, "region", return_value="default"),
                patch.object(manager, "get_migration_finished_date", return_value=None),
            ):
                yield manager

    @pytest.mark.parametrize("link_type", ["stag_exposed_link", "prod_exposed_link"])
    def test_exposed_links_default_values(self, setup_manager, link_type):
        """测试当没有提供 stag_exposed_link, prod_exposed_link 时使用默认值"""
        # 执行 serialize_data 方法
        result = setup_manager.serialize_data()

        # 验证结果中包含链接字段并且是默认的空字符串
        assert link_type in result
        assert result[link_type] == ""
