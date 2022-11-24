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

pytestmark = pytest.mark.django_db

# Short name
REGION = settings.FOR_TESTS_DEFAULT_REGION


class TestAppModelResourceViewSet:
    def test_create(self, api_client, bk_app, bk_module):
        response = api_client.post(
            f'/regions/{REGION}/app_model_resources/',
            data={
                'application_id': bk_app.id,
                'module_id': bk_module.id,
                'code': bk_app.code,
                'image': 'nginx:latest',
            },
        )
        assert response.status_code == 201
        resp = response.json()
        assert resp['module_id'] == str(bk_module.id)
        assert resp['manifest']['kind'] == 'BkApp'

    def test_create_duplicated(self, api_client, bk_app, bk_module):
        def _create():
            return api_client.post(
                f'/regions/{REGION}/app_model_resources/',
                data={
                    'application_id': bk_app.id,
                    'module_id': bk_module.id,
                    'code': bk_app.code,
                    'image': 'nginx:latest',
                },
            )

        resp = _create()
        assert resp.status_code == 201
        resp_dup = _create()
        assert resp_dup.status_code == 400
