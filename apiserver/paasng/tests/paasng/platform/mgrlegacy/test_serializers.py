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
from typing import Any, Dict

import pytest

from paasng.platform.mgrlegacy.serializers import LegacyAppSLZ


class TestLegacyAppSLZ:
    """测试 LegacyAppSLZ 序列化器"""

    @pytest.fixture
    def base_data(self) -> Dict[str, Any]:
        """准备基础测试数据"""
        return {
            "category": "test_category",
            "legacy_app_id": 1,
            "code": "test_app",
            "name": "测试应用",
            "logo": "http://example.com/logo.png",
            "tag": "test_tag",
            "not_support_reasons": [],
            "language": "Python",
            "created": datetime.datetime.now(),
            "latest_migration_id": 1,
            "finished_migration": False,
            "is_active": True,
            "is_prod_deployed": False,
            "has_prod_deployed_before_migration": False,
            # 注意这里没有 stag_exposed_link 字段
            "prod_exposed_link": "http://example.com/prod",
            "region": "test_region",
            "migration_finished_date": datetime.datetime.now(),
            "legacy_url": "http://example.com/legacy",
        }

    def test_missing_stag_exposed_link(self, base_data):
        """测试当输入数据中没有 stag_exposed_link 字段时，序列化器应该使用默认值"""
        # 确保测试数据中没有 stag_exposed_link 字段
        assert "stag_exposed_link" not in base_data

        # 序列化
        serializer = LegacyAppSLZ(data=base_data)

        # 验证序列化是否成功，不应该抛出异常
        assert serializer.is_valid(), f"验证失败，错误: {serializer.errors}"

        # 验证 stag_exposed_link 字段的默认值是否为空字符串
        assert serializer.validated_data["stag_exposed_link"] == ""

    def test_with_stag_exposed_link(self, base_data):
        """测试当输入数据中有 stag_exposed_link 字段时，序列化器应该使用该值"""
        # 添加 stag_exposed_link 字段
        base_data["stag_exposed_link"] = "http://example.com/stag"

        # 序列化
        serializer = LegacyAppSLZ(data=base_data)

        # 验证序列化是否成功
        assert serializer.is_valid(), f"验证失败，错误: {serializer.errors}"

        # 验证 stag_exposed_link 字段是否与输入值相同
        assert serializer.validated_data["stag_exposed_link"] == "http://example.com/stag"
