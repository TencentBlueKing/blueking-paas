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

import arrow
import pytest
from blue_krill.auth.jwt import ClientJWTAuth
from requests import RequestException

from paasng.accessories.servicehub.remote.client import RemoteServiceClient
from paasng.accessories.servicehub.remote.exceptions import RClientResponseError, RemoteClientError
from tests.paasng.accessories.servicehub import data_mocks
from tests.utils.api import mock_json_response


class TestClient:
    @pytest.fixture()
    def client(self, config):
        return RemoteServiceClient(config=config)

    @mock.patch('requests.get')
    def test_list_services_error(self, mocked_get, client):
        mocked_get.side_effect = RequestException('faked requests exception')
        with pytest.raises(RemoteClientError):
            client.list_services()

    @mock.patch('requests.get')
    def test_list_services_status_code_error(self, mocked_get, client):
        mocked_get.return_value = mock_json_response({}, status_code=400)
        with pytest.raises(RClientResponseError):
            client.list_services()

    @mock.patch('requests.get')
    def test_list_services_normal(self, mocked_get, client):
        mocked_get.return_value = mock_json_response(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON)

        assert len(client.list_services()) == 3
        assert mocked_get.called
        assert mocked_get.call_args[0][0] == 'http://faked-host/services/'
        auth_inst = mocked_get.call_args[1]['auth']
        assert isinstance(auth_inst, ClientJWTAuth)

    @mock.patch('requests.get')
    def test_retrieve_instance_normal(self, mocked_get, client):
        mocked_get.return_value = mock_json_response(data_mocks.REMOTE_INSTANCE_JSON)

        data = client.retrieve_instance(instance_id='faked-id')
        assert data is not None
        assert mocked_get.called
        assert mocked_get.call_args[0][0] == 'http://faked-host/instances/faked-id/'
        auth_inst = mocked_get.call_args[1]['auth']
        assert isinstance(auth_inst, ClientJWTAuth)

    @mock.patch('requests.post')
    def test_provision_instance_normal(self, mocked_post, client):
        mocked_post.return_value = mock_json_response(data_mocks.REMOTE_INSTANCE_JSON)

        data = client.provision_instance(
            service_id='faked-svc-id', plan_id='faked-plan-id', instance_id='faked-id', params={'foo': 'bar'}
        )
        assert data is not None
        assert mocked_post.called
        assert mocked_post.call_args[0][0] == 'http://faked-host/services/faked-svc-id/instances/faked-id/'
        auth_inst = mocked_post.call_args[1]['auth']
        assert isinstance(auth_inst, ClientJWTAuth)

    @mock.patch('requests.get')
    def test_retrieve_instance_has_created_field(self, mocked_get, client):
        mocked_get.return_value = mock_json_response(data_mocks.REMOTE_INSTANCE_JSON)

        data = client.retrieve_instance(instance_id='faked-id')
        assert 'created' in data

        # raise nothing
        arrow.get(data['created'])
