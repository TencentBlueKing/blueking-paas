# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import string

import pytest
from django.conf import settings

from paasng.accounts.constants import AccountFeatureFlag as AFF
from paasng.accounts.models import AccountFeatureFlag
from paasng.platform.modules.constants import SourceOrigin
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.fixture
def bk_app_code():
    return generate_random_string(8, string.ascii_lowercase)


@pytest.fixture
def bk_app_name():
    return generate_random_string(8)


@pytest.fixture
def lesscode_public_params():
    return {
        "type": "default",
        "engine_enabled": True,
        "engine_params": {"source_origin": 2, "source_init_template": settings.DUMMY_TEMPLATE_NAME},
    }


class TestApiInAPIGW:
    """Test APIs registered on APIGW, the input and output parameters of these APIs cannot be changed at will"""

    def test_create_lesscode_api(
        self,
        bk_user,
        api_client,
        mock_current_engine_client,
        lesscode_public_params,
        bk_app_code,
        bk_app_name,
        init_tmpls,
    ):
        AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN, True)
        lesscode_public_params.update(
            {
                'region': settings.DEFAULT_REGION_NAME,
                'code': bk_app_code,
                'name': bk_app_name,
            }
        )
        response = api_client.post(
            '/apigw/api/bkapps/applications/',
            data=lesscode_public_params,
        )
        assert response.status_code == 201
        assert response.json()['application']['modules'][0]['source_origin'] == SourceOrigin.BK_LESS_CODE
