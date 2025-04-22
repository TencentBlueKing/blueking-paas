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

from typing import Dict

import pytest

from paasng.accessories.publish.market.models import Tag
from paasng.platform.declarative.application.controller import APP_CODE_FIELD
from paasng.platform.declarative.application.resources import ApplicationDesc, get_application
from paasng.platform.declarative.application.validations.v2 import AppDescriptionSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.serializers import validate_desc
from tests.paasng.platform.declarative.utils import AppDescV2Builder as builder  # noqa: N813
from tests.paasng.platform.declarative.utils import AppDescV2Decorator as decorator  # noqa: N813
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def tag(bk_app):
    """A tag fixture for testing"""
    parent = Tag.objects.create(name="parent test")
    return Tag.objects.create(name="test", parent=parent)


def get_app_description(app_json: Dict) -> ApplicationDesc:
    """A help tool get parse the application json data, describe at app_desc.yml::app to ApplicationDesc"""
    instance = get_application(app_json, APP_CODE_FIELD)
    desc = validate_desc(AppDescriptionSLZ, app_json, instance=instance)
    return desc


class TestValidations:
    """A test suite about v2 validations"""

    def test_normal(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = builder.make_app_desc(
            bk_app_code,
            decorator.with_module(
                module_name="resource",
                is_default=True,
                services=[{"name": "mysql"}],
            ),
            decorator.with_module(
                module_name="frontend",
                is_default=False,
                language="NodeJS",
                services=[{"name": "mysql", "shared_from": "resource"}],
                env_variables=[{"key": "FOO", "value": "value_of_foo", "description": "desc_of_foo"}],
                processes={"web": {"command": "echo 'hello world'"}},
            ),
        )
        desc = get_app_description(app_json)
        assert set(desc.modules) == {"frontend", "resource"}

    def test_invalid_name_length(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=20)}"
        module_name = f"ut{generate_random_string(length=10)}"
        app_json = builder.make_app_desc(bk_app_code, decorator.with_module(module_name, is_default=True))
        with pytest.raises(DescriptionValidationError, match=r"bk_app_code: .*?20"):
            get_app_description(app_json)

    def test_missing_default_module(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = builder.make_app_desc(bk_app_code, decorator.with_module(module_name="foo", is_default=False))
        with pytest.raises(DescriptionValidationError, match="modules"):
            get_app_description(app_json)

    def test_multiple_default_module(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = builder.make_app_desc(
            bk_app_code,
            decorator.with_module(module_name="foo", is_default=True),
            decorator.with_module(module_name="bar", is_default=True),
        )
        with pytest.raises(DescriptionValidationError, match="modules"):
            get_app_description(app_json)

    def test_shared_service_error(self):
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = builder.make_app_desc(
            bk_app_code,
            decorator.with_module(
                module_name="foo",
                is_default=True,
                services=[{"name": "openai", "shared_from": "bar"}],
            ),
        )
        with pytest.raises(DescriptionValidationError, match="modules"):
            get_app_description(app_json)

    def test_nested_shared_service(self):
        """测试多层服务依赖检查 - 不允许模块A引用模块B的服务，而模块B又引用模块C的服务"""
        bk_app_code = f"ut{generate_random_string(length=10)}"

        # 创建一个有3个模块的应用，形成多层服务依赖链
        app_json = builder.make_app_desc(
            bk_app_code,
            # 模块C：提供基础服务
            decorator.with_module(
                module_name="resource",
                is_default=False,
                services=[{"name": "mysql"}],  # 原始服务定义
            ),
            # 模块B：引用模块C的服务
            decorator.with_module(
                module_name="backend",
                is_default=False,
                services=[{"name": "mysql", "shared_from": "resource"}],  # 第一次依赖
            ),
            # 模块A：引用模块B的服务，形成多层依赖
            decorator.with_module(
                module_name="frontend",
                is_default=True,
                services=[{"name": "mysql", "shared_from": "backend"}],  # 第二次依赖，这里应该被拒绝
            ),
        )

        # 验证多层依赖会被拒绝
        with pytest.raises(DescriptionValidationError, match="modules"):
            get_app_description(app_json)
