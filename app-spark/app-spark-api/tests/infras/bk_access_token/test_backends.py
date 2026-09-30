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

"""Each backend sends the request its token service expects, and never lets a secret into an error."""

import json

import httpx2
import pytest

from app_spark_api.infras.bk_access_token import (
    AccessTokenBackend,
    AccessTokenBackendConfig,
    AccessTokenUnavailableError,
    AuthApiBackend,
    SsmBackend,
    UserCredential,
    UserCredentialType,
    get_access_token_backend_cls,
)

AUTH_API_URL = "http://apigw.example.com/auth_api/token/"
SSM_URL = "https://bkssm.example.com/api/v1/auth/access-tokens"
APP_SECRET = "app-secret-value"
LOGIN_VALUE = "login-cookie-value"

TICKET = UserCredential(type=UserCredentialType.BK_TICKET, value=LOGIN_VALUE, username="alice")
BK_TOKEN = UserCredential(type=UserCredentialType.BK_TOKEN, value=LOGIN_VALUE, username="alice")


def make_backend(
    backend_cls: type[AccessTokenBackend], token_url: str, handler
) -> tuple[AccessTokenBackend, list[httpx2.Request]]:
    """Build a backend whose requests are recorded and answered by ``handler``."""
    requests: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return handler(request)

    config = AccessTokenBackendConfig(token_url=token_url, app_code="bk-app-spark", app_secret=APP_SECRET)
    return backend_cls(config, transport=httpx2.MockTransport(record)), requests


def answer_token(token: str = "user-token"):
    """Return a handler that issues ``token`` the way both token services do."""
    return lambda _: httpx2.Response(200, json={"code": 0, "data": {"access_token": token}})


async def test_auth_api_exchanges_bk_ticket_and_asks_to_reuse_a_valid_token():
    backend, requests = make_backend(AuthApiBackend, AUTH_API_URL, answer_token())

    assert await backend.fetch_user_token(TICKET) == "user-token"

    (request,) = requests
    assert str(request.url) == AUTH_API_URL
    assert json.loads(request.content) == {
        "app_code": "bk-app-spark",
        "app_secret": APP_SECRET,
        "env_name": "prod",
        "grant_type": "authorization_code",
        "rtx": "alice",
        "bk_ticket": LOGIN_VALUE,
        "need_new_token": 0,
    }


async def test_ssm_exchanges_bk_token_with_the_app_identity_in_headers_only():
    backend, requests = make_backend(SsmBackend, SSM_URL, answer_token())

    assert await backend.fetch_user_token(BK_TOKEN) == "user-token"

    (request,) = requests
    assert str(request.url) == SSM_URL
    assert request.headers["X-BK-APP-CODE"] == "bk-app-spark"
    assert request.headers["X-BK-APP-SECRET"] == APP_SECRET
    # 这个签发接口本身就复用未过期的 token，不需要也不认 need_new_token；app_secret 不进请求体。
    assert json.loads(request.content) == {
        "grant_type": "authorization_code",
        "id_provider": "bk_login",
        "bk_token": LOGIN_VALUE,
    }


@pytest.mark.parametrize(
    ("backend_cls", "credential"),
    [
        pytest.param(AuthApiBackend, BK_TOKEN, id="auth-api-given-bk-token"),
        pytest.param(SsmBackend, TICKET, id="ssm-given-bk-ticket"),
    ],
)
async def test_a_login_of_the_other_type_is_never_sent(backend_cls, credential):
    backend, requests = make_backend(backend_cls, AUTH_API_URL, answer_token())

    with pytest.raises(AccessTokenUnavailableError):
        await backend.fetch_user_token(credential)
    assert requests == []


@pytest.mark.parametrize(
    ("backend_type", "backend_cls"),
    [("bk_token", SsmBackend), ("bk_ticket", AuthApiBackend)],
)
def test_backend_follows_bkauth_backend_type(settings, backend_type, backend_cls):
    settings.BKAUTH_BACKEND_TYPE = backend_type

    assert get_access_token_backend_cls() is backend_cls


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx2.Response(500, json={"message": f"bad secret {APP_SECRET}"}), id="refused"),
        pytest.param(httpx2.Response(200, json={"code": 1, "data": None}), id="empty-data"),
        pytest.param(httpx2.Response(200, json={"data": {"access_token": ""}}), id="empty-token"),
        pytest.param(httpx2.Response(200, text="not json"), id="not-json"),
        # JSON 数组走 AttributeError：.get 不存在，不能当成「有 data 字段的 mapping」。
        pytest.param(httpx2.Response(200, json=["not", "a", "mapping"]), id="json-array"),
    ],
)
async def test_a_failed_exchange_is_reported_without_echoing_secrets(response):
    backend, _ = make_backend(AuthApiBackend, AUTH_API_URL, lambda _: response)

    with pytest.raises(AccessTokenUnavailableError) as exc_info:
        await backend.fetch_user_token(TICKET)

    assert APP_SECRET not in str(exc_info.value)
    assert LOGIN_VALUE not in str(exc_info.value)


async def test_an_unreachable_token_service_is_an_unavailable_token():
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    backend, _ = make_backend(SsmBackend, SSM_URL, refuse)

    with pytest.raises(AccessTokenUnavailableError):
        await backend.fetch_user_token(BK_TOKEN)
