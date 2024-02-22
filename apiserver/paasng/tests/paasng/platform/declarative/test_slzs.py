# -*- coding: utf-8 -*-
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
from typing import Dict

import pytest

from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.application.serializers import AppDescriptionSLZ
from paasng.platform.declarative.application.validations import v2, v3
from paasng.platform.declarative.serializers import validate_desc
from tests.paasng.platform.declarative.utils import AppDescV2Builder as v2_builder  # noqa: N813
from tests.paasng.platform.declarative.utils import AppDescV3Builder as v3_builder  # noqa: N813
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def get_app_description(slz_class, app_json: Dict) -> ApplicationDesc:
    """A help tool get parse the application json data, describe at app_desc.yml::app to ApplicationDesc"""
    desc = validate_desc(slz_class, app_json, instance=None)
    return desc


class TestAppDescriptionSLZ:
    def test_v2(self):
        random_name = f"ut{generate_random_string(length=10)}"
        app_desc_json = v2_builder.make_app_desc(
            random_name,
            v2_builder.with_module(
                "nodejs",
                is_default=True,
                language="nodejs",
                processes={"web": {"command": "npm run server"}},
                services=[{"name": "mysql", "shared_from": "python"}],
            ),
            v2_builder.with_module(
                "python",
                is_default=False,
                language="python",
                processes={
                    "beat": {"command": "python manage.py celery beat -l info", "replicas": 1},
                    "web": {
                        "command": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile -",
                        "replicas": 2,
                    },
                },
                services=[{"name": "mysql"}],
            ),
        )
        app_desc = get_app_description(v2.AppDescriptionSLZ, app_desc_json)

        slz = AppDescriptionSLZ(app_desc)
        data = slz.data

        # 不管设置了什么 app_desc 设置了多少个 processes, 使用 AppDescriptionSLZ 序列化后都不会出现在 spec 中
        assert data == {
            "region": None,
            "code": random_name,
            "market": None,
            "modules": {
                "nodejs": {
                    "name": "nodejs",
                    "isDefault": True,
                    "spec": {
                        "addons": [{"name": "mysql", "specs": [], "moduleRef": {"moduleName": "python"}}],
                    },
                },
                "python": {
                    "name": "python",
                    "isDefault": False,
                    "spec": {
                        "addons": [{"name": "mysql", "specs": []}],
                    },
                },
            },
            "name_zh_cn": random_name,
            "name_en": random_name,
        }

    def test_v3(self):
        random_name = f"ut{generate_random_string(length=10)}"
        app_desc_json = v3_builder.make_app_desc(
            random_name,
            v3_builder.with_module(
                "nodejs",
                is_default=True,
                language="nodejs",
                module_spec={"processes": [{"name": "web", "command": ["npm", "run", "server"]}]},
            ),
            v3_builder.with_module(
                "python",
                is_default=False,
                language="python",
                module_spec={
                    "processes": [
                        {
                            "name": "beat",
                            "command": ["python"],
                            "args": ["manage.py", "celery", "beat", "-l", "info"],
                            "replicas": 1,
                        },
                        {
                            "name": "web",
                            "command": ["gunicorn"],
                            "args": ["wsgi"],
                            "replicas": 2,
                        },
                    ]
                },
            ),
        )
        app_desc = get_app_description(v3.AppDescriptionSLZ, app_desc_json)

        slz = AppDescriptionSLZ(app_desc)
        data = slz.data

        assert data == {
            "region": None,
            "code": random_name,
            "market": None,
            "modules": {
                "nodejs": {
                    "name": "nodejs",
                    "isDefault": True,
                    "spec": {"processes": [{"name": "web", "command": ["npm", "run", "server"]}]},
                },
                "python": {
                    "name": "python",
                    "isDefault": False,
                    "spec": {
                        "processes": [
                            {
                                "name": "beat",
                                "command": ["python"],
                                "args": ["manage.py", "celery", "beat", "-l", "info"],
                                "replicas": 1,
                            },
                            {
                                "name": "web",
                                "command": ["gunicorn"],
                                "args": ["wsgi"],
                                "replicas": 2,
                            },
                        ]
                    },
                },
            },
            "name_zh_cn": random_name,
            "name_en": random_name,
        }
