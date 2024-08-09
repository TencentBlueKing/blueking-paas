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

from typing import Dict

import pytest

from paasng.accessories.publish.market.models import Product
from paasng.accessories.publish.sync_market.handlers import (
    on_change_application_name,
    prepare_change_application_name,
)
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.platform.declarative.application.resources import ServiceSpec
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.handlers import SMartDescriptionHandler, get_desc_handler
from paasng.platform.declarative.models import DeploymentDescription

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSMartDescriptionHandler:
    @pytest.fixture()
    def app_desc(self, one_px_png) -> Dict:
        return {
            "author": "blueking",
            "introduction": "blueking app",
            "is_use_celery": False,
            "version": "0.0.1",
            "env": [],
            "logo_b64data": one_px_png,
        }

    def test_app_creation(self, random_name, bk_user, app_desc, one_px_png):
        app_desc.update(
            {
                "app_code": random_name,
                "app_name": random_name,
            }
        )
        SMartDescriptionHandler(app_desc).handle_app(bk_user)
        application = Application.objects.get(code=random_name)
        assert application is not None
        # 由于 ProcessedImageField 会将 logo 扩展为 144,144, 因此这里判断对应的位置的标记位
        logo_content = application.logo.read()
        assert logo_content[19] == 144
        assert logo_content[23] == 144

    def test_app_update_existed(self, bk_app, bk_user, app_desc):
        prepare_change_application_name.disconnect(on_change_application_name)
        app_desc.update(
            {
                "app_code": bk_app.code,
                "app_name": bk_app.name,
                "desktop": {"width": 303, "height": 100},
            }
        )
        SMartDescriptionHandler(app_desc).handle_app(bk_user)
        product = Product.objects.get(code=bk_app.code)
        assert product.displayoptions.width == 303

    @pytest.mark.parametrize(
        ("memory", "expected_plan_name"),
        [
            (512, "default"),
            (1024, "default"),
            (1536, "4C2G"),
            (2048, "4C2G"),
            (3072, "4C4G"),
            (4096, "4C4G"),
            (8192, "4C4G"),
        ],
    )
    def test_bind_process_spec_plans(self, random_name, bk_deployment, app_desc, memory, expected_plan_name):
        app_desc.update(
            {
                "app_code": random_name,
                "app_name": random_name,
                "env": [{"key": "BKAPP_FOO", "value": "1"}],
                "container": {"memory": memory},
            }
        )
        SMartDescriptionHandler(app_desc).handle_deployment(bk_deployment)

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert desc_obj.spec.processes[0].resQuotaPlan == expected_plan_name

    @pytest.mark.parametrize(
        ("is_use_celery", "expected_services"),
        [
            (True, [ServiceSpec(name="mysql"), ServiceSpec(name="rabbitmq")]),
            (False, [ServiceSpec(name="mysql")]),
        ],
    )
    def test_app_data_to_desc(self, random_name, app_desc, is_use_celery, expected_services):
        app_desc.update({"app_code": random_name, "app_name": random_name, "is_use_celery": is_use_celery})
        assert SMartDescriptionHandler(app_desc).app_desc.default_module.services == expected_services

    @pytest.mark.parametrize(
        ("libraries", "expected"), [([], []), ([dict(name="foo", version="bar")], [dict(name="foo", version="bar")])]
    )
    def test_libraries(self, random_name, app_desc, libraries, expected):
        app_desc.update({"app_code": random_name, "app_name": random_name, "libraries": libraries})
        plugin = SMartDescriptionHandler(app_desc).app_desc.get_plugin(AppDescPluginType.APP_LIBRARIES)
        assert plugin
        assert plugin["data"] == expected


def test_app_data_to_desc(random_name):
    app_data = {
        "author": "blueking",
        "introduction": "blueking app",
        "is_use_celery": False,
        "version": "0.0.1",
        "env": [],
        "language": "python",
        "app_code": random_name,
        "app_name": random_name,
    }
    desc = get_desc_handler(app_data).app_desc
    assert desc.name_zh_cn == random_name
    assert desc.code == random_name
    plugin = desc.get_plugin(AppDescPluginType.APP_VERSION)
    assert plugin
    assert plugin["data"] == "0.0.1"
    assert desc.default_module.language == AppLanguage.PYTHON
