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

from paasng.platform.bkapp_model.serializers.serializers import ModuleProcessSpecsInputSLZ
from paasng.platform.bkapp_model.serializers.v1alpha2 import BkAppSpecInputSLZ, ProcServiceInputSLZ
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH


@pytest.mark.parametrize(
    ("test_data", "error_keyword"),
    [
        ({"processes": [], "configuration": {"env": []}}, "empty"),
        ({"configuration": {"env": []}}, "required"),
    ],
    ids=["empty_processes", "missing_processes"],
)
class TestBkAppSpecInputSLZ:
    """测试 BkAppSpecInputSLZ 序列化器"""

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


class TestProcServiceInputSLZ:
    """测试 ProcServiceInputSLZ 序列化器"""

    @pytest.mark.parametrize(
        ("name", "is_valid"),
        [
            # Invalid cases
            ("test_name", False),
            ("TestName", False),
            ("a" * (PROC_TYPE_MAX_LENGTH + 1), False),
            # Valid case
            ("valid-name", True),
        ],
    )
    def test_service_name_validation(self, name, is_valid):
        """测试服务名称验证，包括下划线约束、模式匹配和长度限制"""
        serializer = ProcServiceInputSLZ(data={"name": name, "targetPort": 8000, "protocol": "TCP", "port": 80})

        assert serializer.is_valid(raise_exception=False) == is_valid

        if not is_valid:
            assert "name" in serializer.errors


class TestProcessNameValidation:
    """测试包含下划线和不包含下划线的进程名称验证"""

    @pytest.mark.parametrize(
        ("process_name", "is_valid", "expected_error"),
        [
            ("web_server", False, "Process names cannot contain underscores"),
            ("webserver", True, None),
        ],
        ids=["name_with_underscore", "name_without_underscore"],
    )
    def test_process_name_validation(self, process_name, is_valid, expected_error):
        data = {
            "proc_specs": [
                {
                    "name": process_name,
                    "command": ["python", "manage.py", "runserver"],
                    "args": [],
                }
            ]
        }

        serializer = ModuleProcessSpecsInputSLZ(data=data)

        if is_valid:
            assert serializer.is_valid()
        else:
            with pytest.raises(ValidationError) as exc:
                serializer.is_valid(raise_exception=True)
            assert expected_error in str(exc.value)


class TestServiceNameInProcessSpec:
    """测试在 proc_specs 中 services.name 的下划线验证"""

    @pytest.mark.parametrize(
        ("service_name", "is_valid", "expected_error"),
        [
            ("service_name", False, "Service names cannot contain underscores"),
            ("service-name", True, None),
        ],
        ids=["service_with_underscore", "service_without_underscore"],
    )
    def test_service_name_in_process_spec(self, service_name, is_valid, expected_error):
        data = {
            "proc_specs": [
                {
                    "name": "web",
                    "command": ["python", "manage.py", "runserver"],
                    "args": [],
                    "services": [{"name": service_name, "target_port": 8000, "protocol": "TCP", "port": 80}],
                }
            ]
        }

        serializer = ModuleProcessSpecsInputSLZ(data=data)

        if is_valid:
            assert serializer.is_valid()
        else:
            with pytest.raises(ValidationError) as exc:
                serializer.is_valid(raise_exception=True)
            assert expected_error in str(exc.value)
