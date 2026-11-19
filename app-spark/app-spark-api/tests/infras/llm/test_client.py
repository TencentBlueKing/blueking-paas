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

"""Calling a model through each of the three sources, and failing without leaking secrets."""

from __future__ import annotations

import json

import httpx2
import pytest
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIChatModel

from app_spark_api.infras.llm import (
    DirectLLMConfig,
    FakeLLMConfig,
    GatewayLLMConfig,
    LLMCallError,
    LLMClient,
    LLMConfigurationError,
    ThinkingConfig,
)
from app_spark_api.infras.llm.models import gateway_model_profile, open_model
from tests.infras.llm.support import (
    OUTPUT_TOOL_NAME,
    RecordingTransport,
    answer_with,
    answer_with_outputs,
)

API_KEY = "sk-direct-secret"
ACCESS_TOKEN = "user-access-token"
GATEWAY_BASE_URL = "https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1"


class TestConfig:
    def test_secrets_stay_out_of_repr(self):
        direct = DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=API_KEY)
        gateway = GatewayLLMConfig(base_url=GATEWAY_BASE_URL, access_token=ACCESS_TOKEN, model_id="hy3")

        assert API_KEY not in repr(direct)
        assert ACCESS_TOKEN not in repr(gateway)

    @pytest.mark.parametrize("model", ["deepseek-v4-flash", "deepseek:", ":deepseek-v4-flash", ""])
    def test_direct_model_needs_a_provider_prefix(self, model):
        with pytest.raises(ValueError, match="model"):
            DirectLLMConfig(model=model, api_key=API_KEY)

    def test_gateway_fields_are_required(self):
        with pytest.raises(ValueError, match="access_token"):
            GatewayLLMConfig(base_url=GATEWAY_BASE_URL, access_token="", model_id="hy3")


class Answer(BaseModel):
    """The answer."""

    value: int = Field(ge=0)


class TestFake:
    async def test_answers_with_the_configured_text(self):
        client = LLMClient(FakeLLMConfig(output="你好"))

        assert await client.run("hi", output_type=str, instructions="be brief") == "你好"

    async def test_answers_with_the_configured_fields(self):
        client = LLMClient(FakeLLMConfig(output={"value": 2}))

        assert await client.run("1 + 1?", output_type=Answer) == Answer(value=2)

    async def test_makes_up_an_answer_that_fits(self):
        client = LLMClient(FakeLLMConfig())

        assert isinstance(await client.run("1 + 1?", output_type=Answer), Answer)


class TestDirect:
    async def test_calls_the_vendor_with_a_bearer_key(self):
        transport = answer_with("hello from deepseek")
        client = LLMClient(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=API_KEY), transport=transport)

        text = await client.run("hi", output_type=str, instructions="be brief", temperature=0.2, max_tokens=32)

        assert text == "hello from deepseek"
        request = transport.requests[-1]
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        body = transport.last_body
        assert body["model"] == "deepseek-v4-flash"
        # pydantic-ai 会在前面加上它自己的 system 说明，所以只看我们给的那两条在不在。
        assert {"role": "system", "content": "be brief"} in body["messages"]
        assert body["messages"][-1] == {"role": "user", "content": "hi"}
        assert body["temperature"] == 0.2
        # 发成 max_tokens 还是 max_completion_tokens 由 pydantic-ai 按厂商决定。
        assert body.get("max_completion_tokens", body.get("max_tokens")) == 32

    async def test_structured_output_is_retried_until_it_validates(self):
        transport = answer_with_outputs({"value": -1}, {"value": 2})
        client = LLMClient(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=API_KEY), transport=transport)

        assert await client.run("1 + 1?", output_type=Answer) == Answer(value=2)

        assert len(transport.requests) == 2
        tools = json.loads(transport.requests[0].content)["tools"]
        assert [tool["function"]["name"] for tool in tools] == [OUTPUT_TOOL_NAME]
        # 第二次请求带着第一次的校验错误，让模型改正。
        assert "greater than or equal to 0" in json.dumps(transport.last_body["messages"])

    async def test_output_that_never_validates_is_a_call_error(self):
        transport = answer_with_outputs(*[{"value": -1}] * 5)
        client = LLMClient(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=API_KEY), transport=transport)

        with pytest.raises(LLMCallError, match="UnexpectedModelBehavior"):
            await client.run("1 + 1?", output_type=Answer)

    async def test_the_vendor_client_is_closed_on_exit(self):
        """Without an injected transport the provider owns its client; leaving the model must close it."""
        async with open_model(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=API_KEY)) as model:
            assert isinstance(model, OpenAIChatModel)
            assert not model.client.is_closed()

        assert model.client.is_closed()

    async def test_unknown_provider_is_a_configuration_error(self):
        client = LLMClient(DirectLLMConfig(model="no-such-vendor:m1", api_key=API_KEY))

        with pytest.raises(LLMConfigurationError, match="no-such-vendor"):
            await client.run("hi", output_type=str)

    async def test_http_error_hides_key_and_body(self):
        body = {"error": {"message": f"invalid key {API_KEY}", "type": "authentication_error"}}
        transport = RecordingTransport(lambda _request: httpx2.Response(401, json=body))
        client = LLMClient(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=API_KEY), transport=transport)

        with pytest.raises(LLMCallError) as exc_info:
            await client.run("hi", output_type=str)

        message = str(exc_info.value)
        assert "HTTP 401" in message
        assert API_KEY not in message
        assert "invalid key" not in message


class TestThinking:
    @pytest.mark.parametrize(
        ("model", "thinking", "expected"),
        [
            # 能关掉思考的模型照关。
            ("deepseek:deepseek-v4-flash", ThinkingConfig(enabled=False), "none"),
            ("deepseek:deepseek-v4-flash", ThinkingConfig(enabled=True, effort="high"), "high"),
            # 关不掉的模型改用指定强度，而不是 pydantic-ai 自己挑的最低强度。
            ("deepseek:deepseek-reasoner", ThinkingConfig(enabled=False, effort="medium"), "medium"),
            # 没有思考开关的模型什么都不发。
            ("deepseek:deepseek-chat", ThinkingConfig(enabled=False), None),
            ("deepseek:deepseek-v4-flash", None, None),
        ],
    )
    async def test_applied_as_far_as_the_model_allows(self, model, thinking, expected):
        transport = answer_with("ok")
        client = LLMClient(DirectLLMConfig(model=model, api_key=API_KEY), transport=transport)

        await client.run("hi", output_type=str, thinking=thinking)

        assert transport.last_body.get("reasoning_effort") == expected

    @pytest.mark.parametrize(
        ("model_id", "thinking", "expected"),
        [
            # 白名单里的模型按借来的上游档设 thinking。
            ("deepseek-v4-flash", ThinkingConfig(enabled=False), "none"),
            ("deepseek-v4-flash", ThinkingConfig(enabled=True, effort="high"), "high"),
            ("qwen3", ThinkingConfig(enabled=False), "none"),
            ("qwen3-5-27B", ThinkingConfig(enabled=False), "none"),
            # 上游档认为关不掉思考的，改用指定强度。
            ("deepseek-reasoner", ThinkingConfig(enabled=False, effort="medium"), "medium"),
            # 匹配了 deepseek-*，但上游档不认为它能设 thinking。
            ("deepseek-v4.1-flash", ThinkingConfig(enabled=False), None),
            # 按我们自己的实测写的档。
            ("hy3", ThinkingConfig(enabled=False), "none"),
            ("hy4", ThinkingConfig(enabled=False), "none"),
            ("hy4-preview", ThinkingConfig(enabled=True, effort="high"), "high"),
            ("hunyuan-turbos", ThinkingConfig(enabled=True, effort="medium"), "medium"),
            # 不在白名单里。qwen3 系列各型号行为不一，没列的不能被别的条目顺带匹配上。
            ("qwen3-235B", ThinkingConfig(enabled=True, effort="high"), None),
            ("qwen3-8b", ThinkingConfig(enabled=False), None),
            ("qwen3-nothinking", ThinkingConfig(enabled=True, effort="medium"), None),
            ("hunyuan-turbos-vision", ThinkingConfig(enabled=False), None),
            ("GLM-5_3-Online-32k", ThinkingConfig(enabled=False), None),
            ("deepseek-v4-flash", None, None),
        ],
    )
    async def test_gateway_thinking_follows_the_whitelist(self, model_id, thinking, expected):
        transport = answer_with("ok")
        config = GatewayLLMConfig(base_url=GATEWAY_BASE_URL, access_token=ACCESS_TOKEN, model_id=model_id)

        await LLMClient(config, transport=transport).run("hi", output_type=str, thinking=thinking)

        body = transport.last_body
        assert body.get("reasoning_effort") == expected
        # 只用 reasoning_effort：厂商自有的开关在网关上不可靠，有的还会 400。
        assert not {"thinking", "chat_template_kwargs", "enable_thinking"} & body.keys()

    def test_gateway_whitelist_matches_case_sensitively(self):
        assert gateway_model_profile("deepseek-v4-flash").get("supports_thinking") is True
        assert gateway_model_profile("DeepSeek-V4-Flash").get("supports_thinking", False) is False


class TestGateway:
    async def test_authenticates_with_the_user_token_only(self):
        transport = answer_with("hello from gateway")
        config = GatewayLLMConfig(base_url=GATEWAY_BASE_URL, access_token=ACCESS_TOKEN, model_id="deepseek-v4.1-flash")
        client = LLMClient(config, transport=transport)

        assert await client.run("hi", output_type=str) == "hello from gateway"

        request = transport.requests[-1]
        assert str(request.url) == f"{GATEWAY_BASE_URL}/chat/completions"
        # 只能带网关认的用户态 token，SDK 自己加的 Bearer 占位必须被拿掉。
        assert "Authorization" not in request.headers
        assert json.loads(request.headers["X-Bkapi-Authorization"]) == {"access_token": ACCESS_TOKEN}
        assert transport.last_body["model"] == "deepseek-v4.1-flash"

    async def test_unreachable_gateway_is_a_call_error(self):
        def refuse(request: httpx2.Request) -> httpx2.Response:
            raise httpx2.ConnectError("refused", request=request)

        config = GatewayLLMConfig(base_url=GATEWAY_BASE_URL, access_token=ACCESS_TOKEN, model_id="hy3")
        client = LLMClient(config, transport=RecordingTransport(refuse))

        with pytest.raises(LLMCallError) as exc_info:
            await client.run("hi", output_type=str)

        assert ACCESS_TOKEN not in str(exc_info.value)


@pytest.mark.live_llm
class TestLive:
    async def test_completes_a_prompt(self, live_llm):
        text = await live_llm.run("只回复数字：1 + 1 等于几？", output_type=str, instructions="你是一个简洁的助手。")

        assert "2" in text

    async def test_answers_with_structured_output(self, live_llm):
        assert await live_llm.run("1 + 1 等于几？", output_type=Answer) == Answer(value=2)

    async def test_answers_with_thinking_off(self, live_llm):
        answer = await live_llm.run("1 + 1 等于几？", output_type=Answer, thinking=ThinkingConfig(enabled=False))

        assert answer == Answer(value=2)
