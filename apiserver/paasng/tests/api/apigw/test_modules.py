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
import pytest
from django.conf import settings

from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.modules.constants import SourceOrigin
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def module_name():
    return generate_random_string(8)


@pytest.fixture()
def create_module_params():
    # 提供给 lesscode 侧的创建模块的公共参数
    return {
        "name": "",
        "source_config": {"source_init_template": settings.DUMMY_TEMPLATE_NAME, "source_origin": 2},
        "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
    }


class TestApiInAPIGW:
    """Test APIs registered on APIGW, the input and output parameters of these APIs cannot be changed at will"""

    @pytest.mark.parametrize(
        ("app_type", "template_name", "language"),
        [
            (ApplicationType.CLOUD_NATIVE.value, "django_legacy", "Python"),
            (ApplicationType.DEFAULT.value, settings.DUMMY_TEMPLATE_NAME, "Python"),
        ],
    )
    def test_create_module(
        self,
        bk_user,
        api_client,
        mock_wl_services_in_creation,
        create_module_params,
        bk_app,
        module_name,
        init_tmpls,
        app_type,
        template_name,
        language,
    ):
        bk_app.type = app_type
        bk_app.save()

        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN, True)
        create_module_params["name"] = module_name
        create_module_params["source_config"]["source_init_template"] = template_name
        response = api_client.post(
            f"/api/bkapps/cloud-native/{bk_app.code}/modules/",
            data=create_module_params,
        )
        assert response.status_code == 201
        assert response.json()["module"]["language"] == language
        assert response.json()["module"]["source_origin"] == SourceOrigin.BK_LESS_CODE
