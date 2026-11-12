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

"""Registering the current user is attempted once and never blocks the caller."""

import json

import httpx2
from django.test import RequestFactory

from app_spark_api.infras.bk_paas import BKAPI_AUTHORIZATION_HEADER
from app_spark_api.infras.bk_paas.registration import aregister_user_profile
from tests.helpers import create_user


def make_request(user, *, cookies: dict[str, str] | None = None):
    """Build a request that login_required has already authenticated as user."""
    request = RequestFactory().get("/")
    request.COOKIES.update(cookies or {})
    request.auth = user
    return request


def configure(settings) -> None:
    """Point both calls at example hosts. The transports never leave the test."""
    settings.BKAUTH_BACKEND_TYPE = "bk_token"
    settings.APP_CODE = "app-spark"
    settings.APP_SECRET = "app-secret-value"
    settings.TOKEN_AUTH_ENDPOINT = "https://bkssm.example.com/api/v1/auth/access-tokens"
    settings.BK_API_URL_TMPL = "https://bkapi.example.com/api/{api_name}/"
    settings.BKPAAS_APIGW_ENVIRONMENT = "prod"
    settings.BKPAAS_APIGW_NAME = "bkpaas3"


def recording_transport(status: int, body) -> tuple[httpx2.MockTransport, list[httpx2.Request]]:
    """Answer every request the same way and keep the requests."""
    requests: list[httpx2.Request] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(status, json=body)

    return httpx2.MockTransport(answer), requests


async def test_a_logged_in_user_is_registered_with_the_exchanged_token(settings):
    configure(settings)
    token_transport, token_requests = recording_transport(200, {"data": {"access_token": "user-token"}})
    paas_transport, paas_requests = recording_transport(200, {"username": "alice", "tenant_id": "default", "role": 2})

    await aregister_user_profile(
        make_request(create_user(username="alice"), cookies={"bk_token": "login-cookie"}),
        token_transport=token_transport,
        paas_transport=paas_transport,
    )

    assert json.loads(token_requests[0].content)["bk_token"] == "login-cookie"
    assert paas_requests[0].url.path == "/api/bkpaas3/prod/accounts/user_profile/"
    assert json.loads(paas_requests[0].headers[BKAPI_AUTHORIZATION_HEADER]) == {
        "bk_app_code": "app-spark",
        "bk_app_secret": "app-secret-value",
        "access_token": "user-token",
    }


async def test_a_refused_registration_does_not_raise(settings):
    configure(settings)
    token_transport, token_requests = recording_transport(200, {"data": {"access_token": "user-token"}})
    paas_transport, paas_requests = recording_transport(403, {"detail": "closed"})

    await aregister_user_profile(
        make_request(create_user(username="alice"), cookies={"bk_token": "login-cookie"}),
        token_transport=token_transport,
        paas_transport=paas_transport,
    )

    # 配置提前失败时同样不会抛。这里要确认请求确实发出去了。
    assert token_requests
    assert paas_requests


async def test_a_request_without_a_blueking_login_is_skipped(settings):
    configure(settings)
    token_transport, token_requests = recording_transport(200, {"data": {"access_token": "user-token"}})
    paas_transport, paas_requests = recording_transport(200, {})

    await aregister_user_profile(
        make_request(create_user(username="alice")),
        token_transport=token_transport,
        paas_transport=paas_transport,
    )

    assert token_requests == []
    assert paas_requests == []
