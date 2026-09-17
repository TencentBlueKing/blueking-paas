# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import base64

import pytest
from rest_framework.test import APIClient

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.open_apis import authentication as iam_auth

pytestmark = pytest.mark.django_db

# 权限中心回调平台资源接口的地址，与注册给权限中心的 callback_url 同一条路径
CALLBACK_URL = "/api/iam-provider/applications/"

SYSTEM_TOKEN = "fake-system-token"


def make_basic_auth(username: str, password: str) -> str:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {credentials}"


@pytest.fixture()
def stub_system_token(monkeypatch):
    """把取系统令牌换成桩，令用例不依赖权限中心

    :param token_or_exc: 令牌字符串；传入异常则表示这一次取令牌失败
    """

    def _stub(token_or_exc):
        def _get_system_token(tenant_id: str) -> str:
            if isinstance(token_or_exc, Exception):
                raise token_or_exc
            return token_or_exc

        monkeypatch.setattr(iam_auth, "get_system_token", _get_system_token)

    return _stub


@pytest.fixture()
def call_callback():
    """以给定的 Authorization 头发起一次回调请求"""
    client = APIClient()
    # 平台故障走未捕获异常产出 5xx，默认配置会把它重新抛出，用例就断不到状态码
    client.raise_request_exception = False

    def _call(authorization: str | None = None):
        headers = {"HTTP_AUTHORIZATION": authorization} if authorization else {}
        return client.post(
            CALLBACK_URL,
            data={"method": "list_instance", "type": "application", "filter": {}, "page": {"limit": 10, "offset": 0}},
            format="json",
            **headers,
        )

    return _call


class TestIAMCallbackAuthentication:
    """权限中心回调的 Basic 认证

    两个版本的凭证形式一致，均为 Basic base64(bk_iam:{system_token})，
    差别只在令牌从哪里取，因此用例统一在取令牌处打桩。
    """

    def test_valid_credentials_pass(self, call_callback, stub_system_token):
        stub_system_token(SYSTEM_TOKEN)

        resp = call_callback(make_basic_auth("bk_iam", SYSTEM_TOKEN))

        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_missing_authorization_is_rejected(self, call_callback, stub_system_token):
        """不带 Authorization 头必须拒绝

        该视图的 permission_classes 为空，认证类若对空凭证返回 None 放行，
        任何人都能拉到全量应用清单。
        """
        stub_system_token(SYSTEM_TOKEN)

        assert call_callback().status_code == 401

    @pytest.mark.parametrize(
        "authorization",
        [
            pytest.param(make_basic_auth("someone", SYSTEM_TOKEN), id="wrong-username"),
            pytest.param(make_basic_auth("bk_iam", "wrong-token"), id="wrong-token"),
            pytest.param(make_basic_auth("bk_iam", ""), id="empty-token"),
            pytest.param("Basic not-base64", id="malformed-credentials"),
            pytest.param("Bearer some-token", id="not-basic-scheme"),
        ],
    )
    def test_bad_credentials_are_rejected(self, call_callback, stub_system_token, authorization):
        stub_system_token(SYSTEM_TOKEN)

        assert call_callback(authorization).status_code == 401

    def test_token_fetch_failure_is_a_server_error(self, call_callback, stub_system_token):
        """取不到令牌时返回 5xx 而不是 401

        取不到令牌是平台故障，调用方的凭证可能完全正确。压成 401 会让权限中心
        按凭证错误处理而不是按服务故障重试。
        """
        stub_system_token(BKIAMGatewayServiceError("bkiam is down"))

        assert call_callback(make_basic_auth("bk_iam", SYSTEM_TOKEN)).status_code >= 500
