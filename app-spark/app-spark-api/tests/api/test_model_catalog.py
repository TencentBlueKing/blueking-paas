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

"""GET /api/models/: which models a user may pick, from the gateway or from the fixed configuration."""

import json
import logging
from functools import partial
from http import HTTPStatus

import httpx2
import pytest

from app_spark_api.agent.model_catalog import services

pytestmark = pytest.mark.django_db(transaction=True)

MODELS_URL = "/api/models/"
SSM_URL = "https://bkssm.example.com/api/v1/auth/access-tokens"
GATEWAY_MODELS_URL = "https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1/models"
ACCESS_TOKEN = "user-access-token"
VENDOR_KEY = "vendor-secret-key"


def make_card(code: str, *, tools: bool | None = True, vision: bool = False, max_model_len: int = 128000) -> dict:
    """Build a model card shaped like the ones the gateway actually returns."""
    properties: dict[str, object] = {
        "default": False,
        "support_vision": vision,
        "support_window": True,
        "support_summary": True,
        "max_model_len": max_model_len,
        "is_self_host": True,
    }
    if tools is not None:
        properties["support_tools"] = tools

    return {"id": code, "object": "model", "created": 1792662210, "owned_by": "aidev", "property": properties}


def make_filler_cards(count: int) -> list[dict]:
    return [make_card(f"filler-{i}") for i in range(count)]


class FakeUpstream:
    """The token service and the bkaidev gateway, behind one transport, recording what they were asked."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.cards: list[dict] = []
        self.gateway_status = HTTPStatus.OK
        self.token_status = HTTPStatus.OK

    @property
    def gateway_requests(self) -> list[httpx2.Request]:
        return [request for request in self.requests if str(request.url) == GATEWAY_MODELS_URL]

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if str(request.url) == SSM_URL:
            return httpx2.Response(self.token_status, json={"data": {"access_token": ACCESS_TOKEN}})

        if str(request.url) == GATEWAY_MODELS_URL:
            return httpx2.Response(self.gateway_status, json={"object": "list", "data": self.cards, "trace_id": "t"})

        return httpx2.Response(HTTPStatus.NOT_FOUND)


@pytest.fixture()
def upstream(monkeypatch) -> FakeUpstream:
    """Route the model list's outbound calls to a fake token service and gateway."""
    fake = FakeUpstream()
    monkeypatch.setattr(
        services, "list_models", partial(services.list_models, transport=httpx2.MockTransport(fake.handle))
    )
    return fake


@pytest.fixture()
def bkaidev_settings(settings):
    """A bkaidev deployment on a bk_token site, recommending nothing."""
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = {"default_model_name": "deepseek-v4-flash"}
    settings.BK_API_URL_TMPL = "https://{api_name}.apigw.example.com"
    settings.APIGW_ENVIRONMENT = "prod"
    settings.BKAUTH_BACKEND_TYPE = "bk_token"
    settings.TOKEN_AUTH_ENDPOINT = SSM_URL
    settings.APP_CODE = "bk-app-spark"
    settings.APP_SECRET = "app-secret-value"
    return settings


@pytest.fixture()
def logged_in_client(aapi_client):
    """A logged-in client that also carries the BlueKing login the token is exchanged with."""
    aapi_client.cookies["bk_token"] = "login-cookie"
    return aapi_client


def collect_codes(body: dict) -> list[str]:
    return [model["code"] for model in body["models"]]


async def test_a_recommended_list_picks_and_orders_the_models(bkaidev_settings, upstream, logged_in_client):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {
        "default_model_name": "deepseek-v4-flash",
        "recommended_models": ["deepseek-v4-flash", "hy3", "GLM-5_3-Online-32k"],
    }
    upstream.cards = [
        make_card("GLM-5_3-Online-32k", max_model_len=32000),
        *make_filler_cards(16),
        make_card("hy3", max_model_len=256000),
        *make_filler_cards(16),
        make_card("deepseek-v4-flash"),
    ]

    response = await logged_in_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert collect_codes(body) == ["deepseek-v4-flash", "hy3", "GLM-5_3-Online-32k"]
    assert (body["source"], body["switchable"], body["default_code"]) == ("bkaidev", True, "deepseek-v4-flash")


async def test_a_model_shows_what_the_gateway_card_says(bkaidev_settings, upstream, logged_in_client):
    """网关卡片没有展示名，用编码代替。"""
    upstream.cards = [make_card("hy3", vision=True, max_model_len=256000)]

    response = await logged_in_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["models"] == [
        {"code": "hy3", "name": "hy3", "context_window": 256000, "supports_vision": True}
    ]


async def test_a_card_without_properties_is_still_offered(bkaidev_settings, upstream, logged_in_client):
    upstream.cards = [{"id": "bare", "object": "model"}]

    response = await logged_in_client.get(MODELS_URL)

    assert response.json()["models"] == [
        {"code": "bare", "name": "bare", "context_window": None, "supports_vision": False}
    ]


async def test_a_recommended_model_the_gateway_does_not_offer_is_left_out_and_logged(
    bkaidev_settings, upstream, logged_in_client, caplog
):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {"default_model_name": "hy3", "recommended_models": ["hy3", "not-exist"]}
    upstream.cards = [make_card("hy3"), make_card("kimi-26")]

    with caplog.at_level(logging.WARNING):
        response = await logged_in_client.get(MODELS_URL)

    assert collect_codes(response.json()) == ["hy3"]
    assert any("not-exist" in record.getMessage() for record in caplog.records if record.levelno == logging.WARNING)


async def test_a_recommended_model_that_cannot_call_tools_is_still_left_out(
    bkaidev_settings, upstream, logged_in_client
):
    """推荐列表只收窄，不放宽：上游说不能调工具的模型，推荐了也不出现。"""
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {
        "default_model_name": "hy3",
        "recommended_models": ["hy3", "hunyuan-turbos-vision"],
    }
    upstream.cards = [make_card("hunyuan-turbos-vision", tools=False, vision=True), make_card("hy3")]

    response = await logged_in_client.get(MODELS_URL)

    assert collect_codes(response.json()) == ["hy3"]


async def test_without_a_recommended_list_every_tool_calling_model_is_offered_in_gateway_order(
    bkaidev_settings, upstream, logged_in_client
):
    upstream.cards = make_filler_cards(35)
    upstream.cards[3] = make_card("aidev-embedding-auto", tools=False)
    upstream.cards[20] = make_card("qwen3-embedding-4B", tools=False)

    response = await logged_in_client.get(MODELS_URL)

    codes = collect_codes(response.json())
    assert len(codes) == 33
    assert codes == [card["id"] for card in upstream.cards if card["property"]["support_tools"]]


async def test_a_model_the_gateway_says_nothing_about_tools_for_is_offered(
    bkaidev_settings, upstream, logged_in_client
):
    upstream.cards = [make_card("deepseek-v4-flash"), make_card("silent", tools=None)]

    response = await logged_in_client.get(MODELS_URL)

    assert collect_codes(response.json()) == ["deepseek-v4-flash", "silent"]


async def test_the_gateway_is_asked_with_the_users_own_token(bkaidev_settings, upstream, logged_in_client):
    await logged_in_client.get(MODELS_URL)

    (request,) = upstream.gateway_requests
    assert json.loads(request.headers["X-Bkapi-Authorization"]) == {"access_token": ACCESS_TOKEN}


async def test_a_failing_gateway_is_an_error_not_an_empty_list(bkaidev_settings, upstream, logged_in_client, caplog):
    upstream.gateway_status = HTTPStatus.INTERNAL_SERVER_ERROR

    response = await logged_in_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert response.json() == {
        "code": "MODEL_CATALOG_UNAVAILABLE",
        "detail": "The model list is unavailable. Please retry later.",
    }
    assert any(record.levelno == logging.ERROR for record in caplog.records)


async def test_a_failing_token_service_is_reported_as_such(bkaidev_settings, upstream, logged_in_client):
    upstream.token_status = HTTPStatus.INTERNAL_SERVER_ERROR

    response = await logged_in_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert response.json()["code"] == "MODEL_ACCESS_TOKEN_UNAVAILABLE"
    assert upstream.gateway_requests == []


async def test_without_a_blueking_login_nothing_is_asked_upstream(bkaidev_settings, upstream, aapi_client):
    """不回落到应用级凭据：没有用户的登录态就不换票，也不调网关。"""
    response = await aapi_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "MODEL_CREDENTIAL_MISSING"
    assert upstream.requests == []


async def test_an_unusable_bkaidev_configuration_is_an_operators_problem(bkaidev_settings, upstream, logged_in_client):
    bkaidev_settings.BK_API_URL_TMPL = ""

    response = await logged_in_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()["code"] == "MODEL_ACCESS_CONFIGURATION_ERROR"


async def test_an_anonymous_caller_is_refused(bkaidev_settings, upstream, aanonymous_api_client):
    response = await aanonymous_api_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert upstream.requests == []


async def test_a_direct_deployment_offers_its_one_model_without_asking_anyone(settings, upstream, aapi_client):
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "deepseek:deepseek-v4-flash", "api_key": VENDOR_KEY}

    response = await aapi_client.get(MODELS_URL)

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert (body["source"], body["switchable"], body["default_code"]) == ("direct", False, "deepseek-v4-flash")
    assert body["models"] == [
        {"code": "deepseek-v4-flash", "name": "deepseek-v4-flash", "context_window": None, "supports_vision": False}
    ]
    assert upstream.requests == []


async def test_a_direct_deployment_never_shows_its_key(settings, upstream, aapi_client):
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "deepseek:deepseek-v4-flash", "api_key": VENDOR_KEY}

    content = (await aapi_client.get(MODELS_URL)).content.decode()

    assert VENDOR_KEY not in content
    assert "api_key" not in content


async def test_a_direct_deployment_shows_its_configured_display_fields(settings, upstream, aapi_client):
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {
        "model": "deepseek:deepseek-v4-flash",
        "api_key": VENDOR_KEY,
        "name": "DeepSeek V4 Flash",
        "context_window": 128000,
    }

    (model,) = (await aapi_client.get(MODELS_URL)).json()["models"]

    assert model == {
        "code": "deepseek-v4-flash",
        "name": "DeepSeek V4 Flash",
        "context_window": 128000,
        "supports_vision": False,
    }
