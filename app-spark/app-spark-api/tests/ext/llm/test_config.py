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

"""Turning the LLM_* settings into the config this service calls models with."""

from __future__ import annotations

import pytest

from app_spark_api.ext.llm.config import build_llm_client, get_llm_config, requires_access_token
from app_spark_api.infras.llm import DirectLLMConfig, FakeLLMConfig, GatewayLLMConfig, LLMConfigurationError


@pytest.fixture
def bkaidev_settings(settings):
    settings.LLM_SOURCE = "bkaidev"
    settings.LLM_BKAIDEV_MODEL_ID = "hy3"
    settings.BK_API_URL_TMPL = "https://{api_name}.apigw.example.com"
    settings.APIGW_ENVIRONMENT = "prod"
    return settings


def test_fake(settings):
    settings.LLM_SOURCE = "fake"

    assert get_llm_config() == FakeLLMConfig()
    assert not requires_access_token()


def test_direct(settings):
    settings.LLM_SOURCE = "direct"
    settings.LLM_DIRECT_CONFIG = {"model": "deepseek:deepseek-v4-flash", "api_key": "sk-test"}

    assert get_llm_config(access_token="ignored") == DirectLLMConfig(
        model="deepseek:deepseek-v4-flash", api_key="sk-test"
    )
    assert not requires_access_token()


@pytest.mark.parametrize(
    "raw_config",
    [{}, {"model": "deepseek:deepseek-v4-flash"}, {"model": "deepseek-v4-flash", "api_key": "sk-test"}],
)
def test_invalid_direct_config(settings, raw_config):
    settings.LLM_SOURCE = "direct"
    settings.LLM_DIRECT_CONFIG = raw_config

    with pytest.raises(LLMConfigurationError):
        get_llm_config()


def test_bkaidev(bkaidev_settings):
    assert requires_access_token()
    assert get_llm_config(access_token="user-token") == GatewayLLMConfig(
        base_url="https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1",
        access_token="user-token",
        model_id="hy3",
    )


def test_bkaidev_needs_a_token(bkaidev_settings):
    with pytest.raises(ValueError, match="access_token"):
        get_llm_config()


def test_bkaidev_without_gateway_url(bkaidev_settings):
    bkaidev_settings.BK_API_URL_TMPL = ""

    with pytest.raises(LLMConfigurationError, match="BK_API_URL_TMPL"):
        get_llm_config(access_token="user-token")


def test_unknown_source(settings):
    settings.LLM_SOURCE = "nope"

    with pytest.raises(LLMConfigurationError, match="LLM_SOURCE"):
        requires_access_token()


async def test_built_client_calls_the_configured_model(settings):
    settings.LLM_SOURCE = "fake"

    assert await build_llm_client().run("hi", output_type=str)
