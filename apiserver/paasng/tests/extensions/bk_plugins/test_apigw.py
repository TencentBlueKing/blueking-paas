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
from unittest.mock import MagicMock, patch

import pytest
from bkapi_client_core.exceptions import BKAPIError
from django_dynamic_fixture import G

from paasng.extensions.bk_plugins.apigw import PluginDefaultAPIGateway, safe_sync_apigw, set_distributors
from paasng.extensions.bk_plugins.exceptions import PluginApiGatewayServiceError
from paasng.extensions.bk_plugins.models import BkPluginDistributor

pytestmark = pytest.mark.django_db


@pytest.fixture
def fake_good_client():
    """Make a fake client which produce successful result"""
    fake_client = MagicMock()
    fake_client.sync_api.return_value = {
        'data': {'id': 1, 'name': 'foo'},
        'code': 0,
        'result': True,
        'message': 'OK',
    }
    empty_payload = {'data': None, 'code': 0, 'result': True, 'message': ''}
    fake_client.grant_permissions.return_value = empty_payload
    fake_client.revoke_permissions.return_value = empty_payload
    return fake_client


@pytest.fixture
def fake_bad_client():
    """Make a fake client which produce failed result"""
    fake_client = MagicMock()
    fake_client.sync_api.side_effect = BKAPIError('foo error')
    fake_client.grant_permissions.side_effect = BKAPIError('foo error')
    fake_client.revoke_permissions.side_effect = BKAPIError('foo error')
    return fake_client


class TestPluginDefaultAPIGateway:
    def test_sync_succeeded(self, bk_plugin_app, fake_good_client):
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_id = apigw_service.sync()

        assert apigw_id == 1
        assert fake_good_client.sync_api.called
        _, kwargs = fake_good_client.sync_api.call_args_list[0]
        assert kwargs['headers']['X-Bkapi-Authorization'] != ''
        assert len(kwargs['data']['maintainers']) > 0

    def test_sync_failed(self, bk_plugin_app, fake_bad_client):
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_bad_client)
        with pytest.raises(PluginApiGatewayServiceError):
            _ = apigw_service.sync()

    def test_sync_reuse_apigw_name(self, bk_plugin_app, fake_good_client):
        bk_plugin_app.bk_plugin_profile.api_gw_name = 'updated_name'
        bk_plugin_app.bk_plugin_profile.save()

        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.sync()

        _, kwargs = fake_good_client.sync_api.call_args_list[0]
        assert kwargs['data']['name'] == 'updated_name', '`sync()` should reuse the name of synced gateway'

    def test_grant_succeeded(self, bk_plugin_app, fake_good_client):
        distributor = G(BkPluginDistributor, code_name='sample-dis-1', bk_app_code='sample-dis-1')
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.grant(distributor)
        assert fake_good_client.grant_permissions.called

    def test_revoke_succeeded(self, bk_plugin_app, fake_good_client):
        distributor = G(BkPluginDistributor, code_name='sample-dis-1', bk_app_code='sample-dis-1')
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.revoke(distributor)
        assert fake_good_client.revoke_permissions.called


def test_safe_sync_apigw_succeeded(bk_plugin_app, fake_good_client):
    with patch(
        "paasng.extensions.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
        return_value=fake_good_client,
    ):
        safe_sync_apigw(bk_plugin_app)
        assert isinstance(bk_plugin_app.bk_plugin_profile.api_gw_id, int)


def test_safe_sync_apigw_failed(bk_plugin_app, fake_bad_client):
    with patch(
        "paasng.extensions.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
        return_value=fake_bad_client,
    ):
        safe_sync_apigw(bk_plugin_app)
        assert bk_plugin_app.bk_plugin_profile.api_gw_id is None


class TestSetDistributors:
    def test_integrated(self, init_tmpls, bk_plugin_app, fake_good_client):
        dis_1 = G(BkPluginDistributor, code_name='sample-dis-1', bk_app_code='sample-dis-1')
        dis_2 = G(BkPluginDistributor, code_name='sample-dis-2', bk_app_code='sample-dis-2')

        with patch(
            "paasng.extensions.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            safe_sync_apigw(bk_plugin_app)
            set_distributors(bk_plugin_app, [dis_1])
            set_distributors(bk_plugin_app, [dis_1, dis_2])
            assert bk_plugin_app.distributors.count() == 2

            set_distributors(bk_plugin_app, [])
            assert bk_plugin_app.distributors.count() == 0

            # Grant permissions should be called twice
            call_args_list = fake_good_client.grant_permissions.call_args_list
            assert len(call_args_list) == 2
            assert [kwargs['data']['target_app_code'] for _, kwargs in call_args_list] == [
                dis_1.bk_app_code,
                dis_2.bk_app_code,
            ]

            # Revoke permissions should be called twice
            call_args_list = fake_good_client.revoke_permissions.call_args_list
            assert len(call_args_list) == 2
            assert [kwargs['data']['target_app_codes'] for _, kwargs in call_args_list] == [
                [dis_1.bk_app_code],
                [dis_2.bk_app_code],
            ]
