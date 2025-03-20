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

import pytest
from rest_framework.exceptions import ValidationError

from paasng.platform.bkapp_model.serializers.v1alpha2 import BkAppSpecInputSLZ


class TestBkAppSpecInputSLZ:
    """测试BkAppSpecInputSLZ序列化器"""

    def test_processes_cannot_be_empty(self):
        """测试processes字段不能为空"""
        # 准备一个包含空processes的数据
        data = {"processes": [], "configuration": {"env": []}}

        # 初始化序列化器
        serializer = BkAppSpecInputSLZ(data=data)

        # 验证序列化器应该报错
        with pytest.raises(ValidationError) as e:
            serializer.is_valid(raise_exception=True)

        # 确认错误信息是 processes 不能为空
        error_msg = str(e.value)
        assert "processes" in error_msg
        assert "empty" in error_msg.lower()

    def test_processes_valid_data(self):
        """提供有效的processes数据作为对比测试"""
        # 准备一个有效的数据，包含至少一个process
        data = {"processes": [{"name": "web", "replicas": 1}], "configuration": {"env": []}}

        # 初始化序列化器
        serializer = BkAppSpecInputSLZ(data=data)

        # 验证序列化应成功
        assert serializer.is_valid(), f"Validation should succeed, but got errors: {serializer.errors}"
