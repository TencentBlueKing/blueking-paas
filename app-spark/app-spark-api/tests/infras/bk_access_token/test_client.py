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

"""AccessTokenClient sends the request apiserver sends, and never lets a secret into an error."""

import json

import httpx2
import pytest

from app_spark_api.infras.bk_access_token import (
    AccessTokenClient,
    AccessTokenClientConfig,
    AccessTokenUnavailableError,
    UserCredential,
    UserCredentialType,
)

TOKEN_URL = "https://bkssm.example.com/api/v1/auth/access-tokens"
APP_SECRET = "app-secret-value"
LOGIN_VALUE = "login-cookie-value"

CONFIG = AccessTokenClientConfig(token_url=TOKEN_URL, app_code="bk-app-spark", app_secret=APP_SECRET)
TICKET = UserCredential(type=UserCredentialType.BK_TICKET, value=LOGIN_VALUE, username="alice")
BK_TOKEN = UserCredential(type=UserCredentialType.BK_TOKEN, value=LOGIN_VALUE, username="alice")


def make_client(handler) -> tuple[AccessTokenClient, list[httpx2.Request]]:
    """Build a client whose requests are recorded and answered by ``handler``."""
    requests: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return handler(request)

    return AccessTokenClient(CONFIG, transport=httpx2.MockTransport(record)), requests


def answer_token(token: str = "user-token"):
    """Return a handler that issues ``token`` the way the token service does."""
    return lambda _: httpx2.Response(200, json={"code": 0, "data": {"access_token": token}})


async def test_bk_ticket_login_asks_the_gateway_to_reuse_a_valid_token():
    client, requests = make_client(answer_token())

    assert await client.fetch_user_token(TICKET) == "user-token"

    (request,) = requests
    assert str(request.url) == TOKEN_URL
    assert request.headers["X-BK-APP-CODE"] == "bk-app-spark"
    assert json.loads(request.content) == {
        "app_code": "bk-app-spark",
        "app_secret": APP_SECRET,
        "env_name": "prod",
        "grant_type": "authorization_code",
        "bk_ticket": LOGIN_VALUE,
        "rtx": "alice",
        "need_new_token": 0,
    }


async def test_bk_token_login_is_verified_by_bk_login():
    client, requests = make_client(answer_token())

    await client.fetch_user_token(BK_TOKEN)

    payload = json.loads(requests[0].content)
    assert payload["bk_token"] == LOGIN_VALUE
    assert payload["id_provider"] == "bk_login"
    assert "bk_ticket" not in payload
    # Not sent by apiserver's BKSSMBackend, which hands its token to one caller. Here a running
    # Runtime keeps using the token, so a new one must not be issued over it.
    assert payload["need_new_token"] == 0


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx2.Response(500, json={"message": f"bad secret {APP_SECRET}"}), id="refused"),
        pytest.param(httpx2.Response(200, json={"code": 1, "data": None}), id="empty-data"),
        pytest.param(httpx2.Response(200, json={"data": {"access_token": ""}}), id="empty-token"),
        pytest.param(httpx2.Response(200, text="not json"), id="not-json"),
    ],
)
async def test_a_failed_exchange_is_reported_without_echoing_secrets(response):
    client, _ = make_client(lambda _: response)

    with pytest.raises(AccessTokenUnavailableError) as exc_info:
        await client.fetch_user_token(TICKET)

    assert APP_SECRET not in str(exc_info.value)
    assert LOGIN_VALUE not in str(exc_info.value)


async def test_an_unreachable_token_service_is_an_unavailable_token():
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    client, _ = make_client(refuse)

    with pytest.raises(AccessTokenUnavailableError):
        await client.fetch_user_token(TICKET)
