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
    """测试 BkAppSpecInputSLZ 序列化器"""

    @pytest.mark.parametrize(
        ("test_data", "error_keyword"),
        [
            ({"processes": [], "configuration": {"env": []}}, "empty"),
            ({"configuration": {"env": []}}, "required"),
        ],
        ids=["empty_processes", "missing_processes"],
    )
    def test_processes_validation(self, test_data, error_keyword):
        """测试 processes 字段验证：不能为空列表且为必填字段"""
        # 初始化序列化器
        serializer = BkAppSpecInputSLZ(data=test_data)

        # 验证序列化器应该报错
        with pytest.raises(ValidationError) as e:
            serializer.is_valid(raise_exception=True)

        # 确认错误信息是 processes 包含预期关键字
        error_msg = str(e.value)
        assert "processes" in error_msg
        assert error_keyword in error_msg.lower()

    def test_env_var_description_field(self):
        """测试环境变量 description 字段能被正确处理"""
        # 创建包含 description 的测试数据
        test_data = {
            "processes": [{"name": "web", "replicas": 1}],
            "configuration": {
                "env": [{"name": "GLOBAL_VAR", "value": "global_value", "description": "全局环境变量描述"}]
            },
            "envOverlay": {
                "envVariables": [
                    {"name": "STAG_VAR", "value": "stag_value", "description": "测试环境特定描述", "envName": "stag"},
                    {"name": "PROD_VAR", "value": "prod_value", "description": "生产环境特定描述", "envName": "prod"},
                ]
            },
        }

        # 初始化并验证序列化器
        serializer = BkAppSpecInputSLZ(data=test_data)
        assert serializer.is_valid(), f"Serializer Validation Error: {serializer.errors}"

        # 提取验证后的数据
        result = serializer.validated_data

        # 验证全局环境变量的描述字段
        assert result.configuration.env[0].description == "全局环境变量描述"

        # 验证环境特定变量的描述字段
        env_var_descriptions = {var.name: var.description for var in result.env_overlay.env_variables}
        assert env_var_descriptions["STAG_VAR"] == "测试环境特定描述"
        assert env_var_descriptions["PROD_VAR"] == "生产环境特定描述"
