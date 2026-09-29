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

"""Which model source a new Runtime gets, and when the token service is asked."""

import json

import httpx2
import pytest

from app_spark_api.agent.runtime import (
    BkAidevModelAccess,
    DirectModelAccess,
    ModelAccessConfigurationError,
    ModelCredentialMissingError,
)
from app_spark_api.agent.runtime.model_access import resolve_model_access
from app_spark_api.infras.bk_access_token import UserCredential, UserCredentialType

APP_SECRET = "app-secret-value"
BKAIDEV_CONFIG = {"default_model_name": "deepseek-v4-pro"}
EXPECTED_BASE_URL = "https://bkapi.example.com/api/bkaidev/prod/openapi/aidev/gateway/llm/v1"
AUTH_API_URL = "http://apigw.example.com/auth_api/token/"
SSM_URL = "https://bkssm.example.com/api/v1/auth/access-tokens"
CREDENTIAL = UserCredential(type=UserCredentialType.BK_TICKET, value="login-cookie", username="alice")


@pytest.fixture()
def bkaidev_settings(settings):
    """Top-level settings every bkaidev resolve needs, on a bk_ticket site."""
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = BKAIDEV_CONFIG
    settings.BK_API_URL_TMPL = "https://bkapi.example.com/api/{api_name}/"
    settings.APIGW_ENVIRONMENT = "prod"
    settings.BKAUTH_BACKEND_TYPE = "bk_ticket"
    settings.TOKEN_AUTH_ENDPOINT = AUTH_API_URL
    settings.AUTH_ENV_NAME = "test"
    settings.APP_CODE = "bk-app-spark"
    settings.APP_SECRET = APP_SECRET
    return settings


@pytest.fixture()
def token_requests() -> list[httpx2.Request]:
    """Requests the fake token service received."""
    return []


@pytest.fixture()
def token_transport(token_requests) -> httpx2.MockTransport:
    """A token service that hands back the same token every time, as a still-valid one would."""

    def issue(request: httpx2.Request) -> httpx2.Response:
        token_requests.append(request)
        return httpx2.Response(200, json={"data": {"access_token": "same-token"}})

    return httpx2.MockTransport(issue)


async def test_bkaidev_source_gets_the_users_token(bkaidev_settings, token_transport):
    access = await resolve_model_access(CREDENTIAL, transport=token_transport)

    assert access == BkAidevModelAccess(
        base_url=EXPECTED_BASE_URL, access_token="same-token", model_name="deepseek-v4-pro"
    )


async def test_an_unset_default_model_name_falls_back_to_deepseek_v4_flash(bkaidev_settings, token_transport):
    # agent 缺 MODEL_NAME 就起不来可用的模型，所以不配也要给一个。
    bkaidev_settings.BKAIDEV_MODEL_CONFIG = {}

    access = await resolve_model_access(CREDENTIAL, transport=token_transport)

    assert access.model_name == "deepseek-v4-flash"


async def test_the_subdomain_template_shape_builds_the_same_llm_path(bkaidev_settings, token_transport):
    bkaidev_settings.BK_API_URL_TMPL = "https://{api_name}.apigw.example.com"

    access = await resolve_model_access(CREDENTIAL, transport=token_transport)

    assert access.base_url == "https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1"


async def test_bk_ticket_site_exchanges_at_token_auth_endpoint(bkaidev_settings, token_transport, token_requests):
    await resolve_model_access(CREDENTIAL, transport=token_transport)

    (request,) = token_requests
    assert str(request.url) == AUTH_API_URL
    payload = json.loads(request.content)
    assert payload["app_code"] == "bk-app-spark"
    assert payload["app_secret"] == APP_SECRET
    assert payload["env_name"] == "test"
    assert payload["bk_ticket"] == "login-cookie"
    assert payload["need_new_token"] == 0


async def test_bk_token_site_exchanges_at_token_auth_endpoint(bkaidev_settings, token_transport, token_requests):
    bkaidev_settings.BKAUTH_BACKEND_TYPE = "bk_token"
    bkaidev_settings.TOKEN_AUTH_ENDPOINT = SSM_URL
    # SsmBackend 不发 env_name，把它配空不该拦下换票。
    bkaidev_settings.AUTH_ENV_NAME = ""
    credential = UserCredential(type=UserCredentialType.BK_TOKEN, value="login-cookie", username="alice")

    access = await resolve_model_access(credential, transport=token_transport)

    assert access.access_token == "same-token"
    (request,) = token_requests
    assert str(request.url) == SSM_URL
    assert json.loads(request.content) == {
        "grant_type": "authorization_code",
        "id_provider": "bk_login",
        "bk_token": "login-cookie",
    }


async def test_the_token_service_is_asked_every_time_and_reuses_the_token(
    bkaidev_settings, token_transport, token_requests
):
    first = await resolve_model_access(CREDENTIAL, transport=token_transport)
    second = await resolve_model_access(CREDENTIAL, transport=token_transport)

    # Nothing kept here between the two: both went to the token service, which hands back the
    # still-valid token instead of issuing one over the first Runtime's.
    assert first.access_token == second.access_token == "same-token"
    assert len(token_requests) == 2


async def test_direct_source_gets_the_fixed_key_and_never_asks_for_a_token(settings, token_transport, token_requests):
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "deepseek:deepseek-v4-flash", "api_key": "vendor-key"}

    access = await resolve_model_access(None, transport=token_transport)

    assert access == DirectModelAccess(model="deepseek:deepseek-v4-flash", api_key="vendor-key")
    assert token_requests == []


async def test_direct_source_without_a_model_is_a_configuration_error(settings):
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {}

    with pytest.raises(ModelAccessConfigurationError):
        await resolve_model_access(CREDENTIAL)


async def test_bkaidev_without_a_login_is_refused(bkaidev_settings, token_transport, token_requests):
    with pytest.raises(ModelCredentialMissingError):
        await resolve_model_access(None, transport=token_transport)
    assert token_requests == []


async def test_incomplete_bkaidev_settings_are_a_configuration_error(
    bkaidev_settings, token_transport, token_requests
):
    # app_secret 只认顶层 APP_SECRET，嵌套配置已经没有这份字段。
    bkaidev_settings.APP_SECRET = ""

    # Reported even without a login: the operator has to fix this, not the user.
    with pytest.raises(ModelAccessConfigurationError) as exc_info:
        await resolve_model_access(None, transport=token_transport)
    assert "APP_SECRET" in str(exc_info.value)
    assert token_requests == []


async def test_missing_token_auth_endpoint_is_a_configuration_error(bkaidev_settings, token_transport, token_requests):
    # 换票地址由部署方填，不从网关模板推导，缺了就报给运维。
    bkaidev_settings.TOKEN_AUTH_ENDPOINT = ""

    with pytest.raises(ModelAccessConfigurationError) as exc_info:
        await resolve_model_access(None, transport=token_transport)
    assert "TOKEN_AUTH_ENDPOINT" in str(exc_info.value)
    assert token_requests == []


@pytest.mark.parametrize(
    "tmpl",
    [
        pytest.param("", id="empty"),
        # format 不会因为没用上 api_name 而报错，不拦的话会拼出少了网关名的地址。
        pytest.param("https://bkapi.example.com/api/", id="no-api-name"),
        pytest.param("https://bkapi.example.com/api/{api_name}/{stage}/", id="other-placeholder"),
    ],
)
async def test_a_bad_apigw_template_is_a_configuration_error(bkaidev_settings, token_transport, token_requests, tmpl):
    bkaidev_settings.BK_API_URL_TMPL = tmpl

    with pytest.raises(ModelAccessConfigurationError) as exc_info:
        await resolve_model_access(None, transport=token_transport)
    assert "BK_API_URL_TMPL" in str(exc_info.value)
    assert token_requests == []


async def test_an_unknown_source_is_a_configuration_error(settings):
    settings.AGENT_MODEL_SOURCE = "openai"

    with pytest.raises(ModelAccessConfigurationError):
        await resolve_model_access(CREDENTIAL)
