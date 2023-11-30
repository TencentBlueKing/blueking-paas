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
from unittest.mock import MagicMock

import pytest
from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from django.test.utils import override_settings

from paasng.platform.bk_lesscode.client import make_bk_lesscode_client
from paasng.platform.bk_lesscode.exceptions import LessCodeApiError
from tests.utils.helpers import generate_random_string


@pytest.fixture(autouse=True)
def _override_default_region():
    with override_settings(ENABLE_BK_LESSCODE_APIGW=True):
        yield


@pytest.fixture()
def fake_good_client():
    """Make a fake client which produce successful result"""
    fake_client = MagicMock()
    fake_client.create_project_by_app.return_value = {
        "code": 0,
        "message": "OK",
        "data": {"projectCode": "appidmodulename", "projectName": "appname"},
    }
    fake_client.find_project_by_app.return_value = {
        "code": 0,
        "message": "OK",
        "data": {
            "id": 168,
            "projectCode": "appidmodulename",
            "projectName": "appname",
            "linkUrl": "/project/168/pages",
        },
    }
    return fake_client


@pytest.fixture()
def fake_bad_client():
    """Make a fake client which produce failed result"""
    fake_client = MagicMock()
    fake_client.create_project_by_app.return_value = {"code": -1, "message": "lesscode平台校验不通过", "data": None}
    fake_client.find_project_by_app.side_effect = APIGatewayResponseError("foo error")
    return fake_client


@pytest.fixture()
def bk_token():
    """user login cookie value"""
    return generate_random_string(length=6)


@pytest.fixture()
def bk_appid():
    return generate_random_string(length=6)


@pytest.fixture()
def bk_app_code():
    return generate_random_string(length=6)


@pytest.fixture()
def bk_app_name():
    return generate_random_string(length=6)


@pytest.fixture()
def bk_module_name():
    return generate_random_string(length=6)


class TestBkLesscode:
    def test_call_api_succeeded(self, bk_token, bk_app_code, bk_app_name, bk_module_name, fake_good_client):
        lesscode_client = make_bk_lesscode_client(bk_token, fake_good_client)
        is_created = lesscode_client.create_app(bk_app_code, bk_app_name, bk_module_name)

        assert is_created is True
        assert fake_good_client.create_project_by_app.called
        _, kwargs = fake_good_client.create_project_by_app.call_args_list[0]
        assert kwargs["headers"]["x-bkapi-authorization"] != ""
        assert kwargs["data"]["appCode"] == bk_app_code
        assert kwargs["data"]["moduleCode"] == bk_module_name

    def test_call_api_failed(self, bk_token, bk_app_code, bk_app_name, bk_module_name, fake_bad_client):
        lesscode_client = make_bk_lesscode_client(bk_token, fake_bad_client)
        with pytest.raises(LessCodeApiError):
            _ = lesscode_client.create_app(bk_app_code, bk_app_name, bk_module_name)

    def test_get_address_succeeded(self, bk_token, bk_app_code, bk_module_name, fake_good_client):
        lesscode_client = make_bk_lesscode_client(bk_token, fake_good_client)
        address = lesscode_client.get_address(bk_app_code, bk_module_name)

        assert address == f"{settings.BK_LESSCODE_URL}/project/168/pages"

    def test_get_address_failed(self, bk_token, bk_app_code, bk_module_name, fake_bad_client):
        lesscode_client = make_bk_lesscode_client(bk_token, fake_bad_client)
        # 获取地址失败时不抛异常，只返回空地址
        address = lesscode_client.get_address(bk_app_code, bk_module_name)
        assert address == ""
