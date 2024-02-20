"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Any, Callable, Dict, Optional

import pytest

from paasng.accessories.publish.market.models import Tag
from paasng.platform.declarative.application.constants import CNATIVE_APP_CODE_FIELD
from paasng.platform.declarative.application.resources import ApplicationDesc, get_application
from paasng.platform.declarative.application.validations.v3 import AppDescriptionSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.serializers import validate_desc
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def tag(bk_app):
    """A tag fixture for testing"""
    parent = Tag.objects.create(name="parent test", region=bk_app.region)
    return Tag.objects.create(name="test", region=bk_app.region, parent=parent)


def get_app_description(app_json: Dict) -> ApplicationDesc:
    """A help tool get parse the application json data, describe at app_desc.yml::app to ApplicationDesc"""
    instance = get_application(app_json, CNATIVE_APP_CODE_FIELD)
    desc = validate_desc(AppDescriptionSLZ, app_json, instance=instance)
    return desc


def make_app_desc(
    random_name: str,
    *applys: Callable,
) -> Dict[str, Any]:
    """Make description data for testing"""
    result: Dict[str, Any] = {
        "bkAppCode": random_name,
        "bkAppName": random_name,
    }
    for apply in applys:
        apply(result)
    return result


def with_module(module_name: str, is_default: bool, module_spec: Optional[Dict] = None):
    def apply(app_desc: Dict):
        if "modules" not in app_desc:
            app_desc["modules"] = []
        for module_desc in app_desc["modules"]:
            if module_desc["name"] == module_name:
                raise ValueError(f"module already exists: name={module_name}")
        app_desc["modules"].append({"name": module_name, "isDefault": is_default, "spec": module_spec or {}})

    return apply


class TestValidateGoodCase:
    """A test suite about v3 validations - good case"""

    def test_one_module(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = make_app_desc(bk_app_code, with_module(module_name="foo", is_default=True))
        get_app_description(app_json)


class TestValidateBadCase:
    """A test suite about v3 validations - bad cases"""

    def test_invalid_name_length(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=20)}"
        app_json = make_app_desc(bk_app_code)
        with pytest.raises(DescriptionValidationError, match="bkAppCode: .*?20"):
            get_app_description(app_json)

    def test_missing_default_module(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = make_app_desc(bk_app_code, with_module(module_name="foo", is_default=False))
        with pytest.raises(DescriptionValidationError, match="modules: 一个应用必须有一个主模块"):
            get_app_description(app_json)

    def test_multiple_default_module(self):
        # 保证应用 ID 是以字母开头
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = make_app_desc(
            bk_app_code,
            with_module(module_name="foo", is_default=True),
            with_module(module_name="bar", is_default=True),
        )
        with pytest.raises(DescriptionValidationError, match="modules: 一个应用只能有一个主模块"):
            get_app_description(app_json)

    def test_share_addon_error(self):
        bk_app_code = f"ut{generate_random_string(length=10)}"
        app_json = make_app_desc(
            bk_app_code,
            with_module(
                module_name="foo",
                is_default=True,
                module_spec={"addons": [{"name": "openai", "moduleRef": {"moduleName": "bar"}}]},
            ),
        )
        with pytest.raises(
            DescriptionValidationError, match=r"modules\[0\].spec.addons: 提供共享增强服务的模块不存在"
        ):
            get_app_description(app_json)
