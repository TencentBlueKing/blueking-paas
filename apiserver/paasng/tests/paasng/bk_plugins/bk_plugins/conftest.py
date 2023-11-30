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

from paasng.bk_plugins.bk_plugins.models import BkPlugin


@pytest.fixture()
def bk_plugin(bk_plugin_app):
    return BkPlugin.from_application(bk_plugin_app)


@pytest.fixture()
def mock_apigw_api_client():
    """Replace the default API Gateway client with a fake client which produce successful result"""
    fake_client = mock.MagicMock()
    fake_client.sync_api.return_value = {
        "data": {"id": 1, "name": "foo"},
        "code": 0,
        "result": True,
        "message": "OK",
    }
    fake_client.grant_permissions.return_value = {
        "data": None,
        "code": 0,
        "result": True,
        "message": "",
    }
    with mock.patch(
        "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
        return_value=fake_client,
    ):
        yield fake_client
