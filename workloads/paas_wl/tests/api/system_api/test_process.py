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
from unittest import mock

import pytest
from django.utils.crypto import get_random_string

from tests.utils.mocks.bcs_client import StubBCSClient

pytestmark = pytest.mark.django_db


class TestProcessViewSet:
    @pytest.mark.mock_get_structured_app
    @pytest.mark.auto_create_ns
    def test_list_processes_statuses(self, api_client, scale_url, create_release):
        assert create_release().status_code == 201
        response = api_client.get(scale_url)
        assert response.status_code == 200
        assert response.json()['count'] == 1


class TestProcessInstanceViewSet:
    @mock.patch("paas_wl.platform.system_api.views.BCSClient", new=StubBCSClient)
    def test_create_webconsole(self, bk_user, api_client, webconsole_url):
        response = api_client.post(
            webconsole_url, data={'operator': bk_user.username, 'container_name': get_random_string(8)}
        )
        data = response.data['data']
        assert data['session_id']
        assert data['web_console_url']
