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
from django.urls import reverse

from paas_wl.cnative.specs.constants import BKPAAS_ADDONS_ANNO_KEY
from paasng.dev_resources.servicehub.services import ServiceObj
from tests.utils import mock

pytestmark = pytest.mark.django_db


class TestCNative:
    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        with mock.patch(
            'paasng.cnative.views.mixed_service_mgr.list_binded',
            new=lambda *args, **kwargs: [
                ServiceObj(region=settings.DEFAULT_REGION_NAME, uuid='xxx', name='mysql', logo='', is_visible=True),
                ServiceObj(region=settings.DEFAULT_REGION_NAME, uuid='xxx', name='redis', logo='', is_visible=True),
            ],
        ):
            yield

    def test_retrieve(self, api_client, bk_stag_env):
        url = reverse(
            'api.cnative.retrieve_manifest_ext',
            kwargs={
                'code': bk_stag_env.application.code,
                'environment': bk_stag_env.environment,
            },
        )
        response = api_client.get(url)
        assert response.data == {'metadata': {'annotations': {BKPAAS_ADDONS_ANNO_KEY: '["mysql", "redis"]'}}}
