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
import logging

import pytest
from django_dynamic_fixture import G

from paasng.platform.engine.models import ConfigVar
from paasng.bk_plugins.bk_plugins.apigw import safe_sync_apigw
from paasng.bk_plugins.bk_plugins.models import BkPluginDistributor

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _setup_fixtures():
    # Default distributors
    G(BkPluginDistributor, code_name='sample-dis-1', bk_app_code='sample-dis-1')
    G(BkPluginDistributor, code_name='sample-dis-2', bk_app_code='sample-dis-2')


class TestDistributors:
    def test_list(self, api_client):
        response = api_client.get('/api/bk_plugin_distributors/')
        assert response.status_code == 200, f'error: {response.json()["detail"]}'
        assert len(response.json()) == 2


class TestDistributorRels:
    """Test APIS of managing distributors of a single bk_plugin"""

    @pytest.fixture(autouse=True)
    def do_preparations(self, bk_plugin_app, mock_apigw_api_client):
        safe_sync_apigw(bk_plugin_app)
        yield

    def test_update(self, bk_plugin_app, api_client):
        """Test updating a plugin's distributors"""
        response = api_client.put(
            f'/api/bk_plugins/{bk_plugin_app.code}/distributors/', {'distributors': ['sample-dis-1', 'sample-dis-2']}
        )
        assert response.status_code == 200, f'error: {response.json()["detail"]}'
        assert len(response.json()) == 2

    def test_integrated(self, bk_plugin_app, api_client):
        """Test both update and list operations"""
        api_client.put(f'/api/bk_plugins/{bk_plugin_app.code}/distributors/', {'distributors': []})
        resp = api_client.get(f'/api/bk_plugins/{bk_plugin_app.code}/distributors/')
        assert len(resp.json()) == 0

        api_client.put(f'/api/bk_plugins/{bk_plugin_app.code}/distributors/', {'distributors': ['sample-dis-1']})
        resp = api_client.get(f'/api/bk_plugins/{bk_plugin_app.code}/distributors/')
        assert len(resp.json()) == 1


class TestPluginConfigurationViewSet:
    """Test APIS of syncing configurations"""

    def test_sync(self, bk_plugin_app, sys_api_client):
        module = bk_plugin_app.get_default_module()
        assert ConfigVar.objects.filter(module=module).count() == 0
        response = sys_api_client.post(
            f"/sys/api/plugins_center/bk_plugins/{bk_plugin_app.code}/configuration/",
            data=[{"key": "FOO", "value": "foo"}, {"key": "BAR", "value": "bar"}, {"key": "BAZ", "value": "baz"}],
        )
        assert response.status_code == 200
        assert ConfigVar.objects.filter(module=module).count() == 3
        assert ConfigVar.objects.get(module=module, key="FOO").value == "foo"
        assert ConfigVar.objects.get(module=module, key="BAR").value == "bar"
        assert ConfigVar.objects.get(module=module, key="BAZ").value == "baz"
        response = sys_api_client.post(
            f"/sys/api/plugins_center/bk_plugins/{bk_plugin_app.code}/configuration/",
            data=[
                {"key": "FOO", "value": "foo"},
                {"key": "BAR", "value": "BAR"},
            ],
        )
        assert response.status_code == 200
        assert ConfigVar.objects.filter(module=module).count() == 2
        assert ConfigVar.objects.get(module=module, key="FOO").value == "foo"
        assert ConfigVar.objects.get(module=module, key="BAR").value == "BAR"
