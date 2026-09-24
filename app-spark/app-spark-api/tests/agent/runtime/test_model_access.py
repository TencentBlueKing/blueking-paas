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

TOKEN_CONFIG = {
    "token_url": "https://bkssm.example.com/api/v1/auth/access-tokens",
    "app_code": "bk-app-spark",
    "app_secret": "app-secret-value",
}
BKAIDEV_CONFIG = {
    "base_url": "https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1",
    "model_name": "deepseek-v4-flash",
    "token": TOKEN_CONFIG,
}
CREDENTIAL = UserCredential(type=UserCredentialType.BK_TICKET, value="login-cookie", username="alice")


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


async def test_bkaidev_source_gets_the_users_token(settings, token_transport):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = BKAIDEV_CONFIG

    access = await resolve_model_access(CREDENTIAL, transport=token_transport)

    assert access == BkAidevModelAccess(
        base_url=BKAIDEV_CONFIG["base_url"], model_name="deepseek-v4-flash", access_token="same-token"
    )


@pytest.mark.parametrize("credential_type", list(UserCredentialType))
async def test_the_token_service_is_asked_every_time_and_reuses_the_token(
    settings, token_transport, token_requests, credential_type
):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = BKAIDEV_CONFIG
    credential = UserCredential(type=credential_type, value="login-cookie", username="alice")

    first = await resolve_model_access(credential, transport=token_transport)
    second = await resolve_model_access(credential, transport=token_transport)

    # Nothing kept here between the two: both went to the token service, and both asked it not
    # to issue a new token, which is what keeps the first Runtime's token alive.
    assert first is not None
    assert second is not None
    assert first.access_token == second.access_token == "same-token"
    assert len(token_requests) == 2
    assert all(json.loads(request.content)["need_new_token"] == 0 for request in token_requests)


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


async def test_bkaidev_without_a_login_is_refused(settings, token_transport, token_requests):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = BKAIDEV_CONFIG

    with pytest.raises(ModelCredentialMissingError):
        await resolve_model_access(None, transport=token_transport)
    assert token_requests == []


async def test_incomplete_bkaidev_settings_are_a_configuration_error(settings, token_transport, token_requests):
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = {
        **BKAIDEV_CONFIG,
        "token": {k: v for k, v in TOKEN_CONFIG.items() if k != "app_secret"},
    }

    # Reported even without a login: the operator has to fix this, not the user.
    with pytest.raises(ModelAccessConfigurationError) as exc_info:
        await resolve_model_access(None, transport=token_transport)
    assert "app_secret" in str(exc_info.value)
    assert token_requests == []


async def test_an_unknown_source_is_a_configuration_error(settings):
    settings.AGENT_MODEL_SOURCE = "openai"

    with pytest.raises(ModelAccessConfigurationError):
        await resolve_model_access(CREDENTIAL)
