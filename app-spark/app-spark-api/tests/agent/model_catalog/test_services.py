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

"""The model a new Runtime starts with and the model one turn may ask for, both read off the model list."""

import logging
from http import HTTPStatus

import httpx2
import pytest

from app_spark_api.agent.model_catalog import services
from app_spark_api.agent.model_catalog.services import resolve_model_access, resolve_run_model_id
from app_spark_api.agent.runtime import (
    BkAidevModelAccess,
    DirectModelAccess,
    ModelAccessConfigurationError,
    ModelNotAvailableError,
)
from app_spark_api.infras.bk_access_token import UserCredential, UserCredentialType

SSM_URL = "https://bkssm.example.com/api/v1/auth/access-tokens"
LLM_BASE_URL = "https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1"
ACCESS_TOKEN = "user-access-token"
CREDENTIAL = UserCredential(type=UserCredentialType.BK_TOKEN, value="login-cookie", username="alice")


class FakeUpstream:
    """The token service and the bkaidev gateway, behind one transport, recording what they were asked."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.model_ids: list[str] = []

    @property
    def transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.handle)

    def collect_urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if str(request.url) == SSM_URL:
            return httpx2.Response(HTTPStatus.OK, json={"data": {"access_token": ACCESS_TOKEN}})

        if str(request.url) == f"{LLM_BASE_URL}/models":
            cards = [{"id": model_id, "property": {"support_tools": True}} for model_id in self.model_ids]
            return httpx2.Response(HTTPStatus.OK, json={"object": "list", "data": cards})

        return httpx2.Response(HTTPStatus.NOT_FOUND)


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    """Give every test a fresh, empty gateway model cache."""
    monkeypatch.setattr(services, "gateway_models_cache", services.GatewayModelsCache())


@pytest.fixture()
def upstream() -> FakeUpstream:
    return FakeUpstream()


@pytest.fixture()
def bkaidev_settings(settings):
    """A bkaidev deployment on a bk_token site, narrowing nothing."""
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = {"default_model_id": "deepseek-v4-pro"}
    settings.BK_API_URL_TMPL = "https://{api_name}.apigw.example.com"
    settings.BKAIDEV_APIGW_ENVIRONMENT = "prod"
    settings.BKAUTH_BACKEND_TYPE = "bk_token"
    settings.TOKEN_AUTH_ENDPOINT = SSM_URL
    settings.APP_CODE = "bk-app-spark"
    settings.APP_SECRET = "app-secret-value"
    settings.SANDBOX_APP_CODE = "bk-app-spark-pub"
    settings.SANDBOX_APP_SECRET = "pub-secret-value"
    return settings


@pytest.fixture()
def direct_settings(settings):
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "deepseek:deepseek-v4-flash", "api_key": "vendor-key"}
    return settings


# --- The model a new Runtime starts with --------------------------------------------------------


async def test_a_runtime_starts_on_the_configured_default_when_it_is_offered(bkaidev_settings, upstream):
    upstream.model_ids = ["hy3", "deepseek-v4-pro"]

    access = await resolve_model_access(CREDENTIAL, transport=upstream.transport)

    assert access == BkAidevModelAccess(base_url=LLM_BASE_URL, access_token=ACCESS_TOKEN, model_id="deepseek-v4-pro")
    # 换来的 token 既交给 Runtime 也拿去取列表，缓存冷时也只换一次票。
    assert upstream.collect_urls() == [SSM_URL, f"{LLM_BASE_URL}/models"]


async def test_an_unset_default_model_id_falls_back_to_deepseek_v4_flash(bkaidev_settings, upstream):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {}
    upstream.model_ids = ["hy3", "deepseek-v4-flash"]

    access = await resolve_model_access(CREDENTIAL, transport=upstream.transport)

    assert isinstance(access, BkAidevModelAccess)
    assert access.model_id == "deepseek-v4-flash"


@pytest.mark.parametrize(
    ("available", "model_ids"),
    [
        pytest.param(["hy4-*", "hy3"], ["deepseek-v4-pro", "hy3", "hy4-preview"], id="filtered-out-by-the-list"),
        pytest.param([], ["hy3", "hy4-preview"], id="not-offered-by-the-gateway"),
    ],
)
async def test_a_default_not_in_the_list_gives_way_to_the_first_model(
    bkaidev_settings, upstream, caplog, available, model_ids
):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {"default_model_id": "deepseek-v4-pro", "available_models": available}
    upstream.model_ids = model_ids

    with caplog.at_level(logging.WARNING):
        access = await resolve_model_access(CREDENTIAL, transport=upstream.transport)
        catalog = await services.list_models(CREDENTIAL, transport=upstream.transport)

    # 沙箱跑的就是前端标成默认的那个。
    expected = "hy4-preview" if available else "hy3"
    assert isinstance(access, BkAidevModelAccess)
    assert access.model_id == catalog.default_model_id == expected
    assert any("deepseek-v4-pro" in record.getMessage() for record in caplog.records)


async def test_no_default_and_an_empty_list_is_an_operators_problem(bkaidev_settings, upstream):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {"default_model_id": "deepseek-v4-pro", "available_models": ["kimi-*"]}
    upstream.model_ids = ["deepseek-v4-pro", "hy3"]

    with pytest.raises(ModelAccessConfigurationError, match="deepseek-v4-pro"):
        await resolve_model_access(CREDENTIAL, transport=upstream.transport)

    with pytest.raises(ModelAccessConfigurationError):
        await services.list_models(CREDENTIAL, transport=upstream.transport)


async def test_direct_source_gets_the_fixed_key_and_asks_no_one(direct_settings, upstream):
    access = await resolve_model_access(None, transport=upstream.transport)

    assert access == DirectModelAccess(model="deepseek:deepseek-v4-flash", api_key="vendor-key")
    assert upstream.requests == []


async def test_direct_source_without_a_model_is_a_configuration_error(direct_settings):
    direct_settings.AGENT_DIRECT_MODEL_CONFIG = {}

    with pytest.raises(ModelAccessConfigurationError):
        await resolve_model_access(CREDENTIAL)


# --- The model one turn asks for ------------------------------------------------------------


AVAILABLE = ["deepseek-*", "hy3"]


@pytest.mark.parametrize(
    ("available", "model_id"),
    [
        pytest.param(AVAILABLE, "hy3", id="in-the-list"),
        pytest.param(AVAILABLE, "deepseek-v4-flash", id="matched-by-a-pattern"),
        pytest.param([], "kimi-26", id="empty-list-offers-every-gateway-model"),
    ],
)
async def test_bkaidev_forwards_what_the_model_list_offers(bkaidev_settings, upstream, available, model_id):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {"default_model_id": "hy3", "available_models": available}
    upstream.model_ids = ["hy3", "deepseek-v4-flash", "kimi-26"]

    assert await resolve_run_model_id(model_id, CREDENTIAL, transport=upstream.transport) == model_id


@pytest.mark.parametrize(
    ("available", "model_id"),
    [
        pytest.param(AVAILABLE, "kimi-26", id="left-out-by-the-list"),
        # 列表为空也不再原样交给网关：网关没开放的模型同样不在列表里。
        pytest.param([], "qwen3-5-397B", id="not-offered-by-the-gateway"),
    ],
)
async def test_bkaidev_refuses_what_the_model_list_does_not_offer(bkaidev_settings, upstream, available, model_id):
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {"default_model_id": "hy3", "available_models": available}
    upstream.model_ids = ["hy3", "deepseek-v4-flash", "kimi-26"]

    with pytest.raises(ModelNotAvailableError, match=model_id):
        await resolve_run_model_id(model_id, CREDENTIAL, transport=upstream.transport)


async def test_a_turn_naming_no_model_asks_no_one(bkaidev_settings, upstream):
    assert await resolve_run_model_id(None, None, transport=upstream.transport) is None
    assert upstream.requests == []


async def test_a_turn_reads_the_list_from_the_cache(bkaidev_settings, upstream):
    upstream.model_ids = ["deepseek-v4-pro", "hy3"]
    await services.list_models(CREDENTIAL, transport=upstream.transport)
    asked = len(upstream.requests)

    await resolve_run_model_id("hy3", CREDENTIAL, transport=upstream.transport)

    assert len(upstream.requests) == asked


@pytest.mark.parametrize(
    ("model", "model_id"),
    [
        pytest.param("deepseek:deepseek-v4-flash", "deepseek-v4-flash", id="built-in"),
        pytest.param("deepseek-v4-flash", "deepseek-v4-flash", id="built-in-without-provider"),
    ],
)
async def test_direct_never_forwards_its_built_in_model(direct_settings, upstream, model, model_id):
    direct_settings.AGENT_DIRECT_MODEL_CONFIG = {"model": model}

    assert await resolve_run_model_id(model_id, None, transport=upstream.transport) is None
    assert upstream.requests == []


async def test_direct_refuses_any_other_model(direct_settings):
    with pytest.raises(ModelNotAvailableError, match="hy3"):
        await resolve_run_model_id("hy3", None)
