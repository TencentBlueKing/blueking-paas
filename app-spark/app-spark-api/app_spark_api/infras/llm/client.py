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

"""Calling an LLM for a typed answer."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking
from pydantic_ai.exceptions import AgentRunError, ModelHTTPError, UserError

from app_spark_api.infras.llm.exceptions import LLMCallError
from app_spark_api.infras.llm.models import open_model

if TYPE_CHECKING:
    import httpx2
    from pydantic_ai.profiles import ModelProfile
    from pydantic_ai.settings import ModelSettings, ThinkingLevel

    from app_spark_api.infras.llm.entities import LLMConfig, ThinkingConfig

DEFAULT_TIMEOUT_SECONDS = 60.0

OutputT = TypeVar("OutputT")


class LLMClient:
    """Ask a model for an answer of a given type, wherever the config points it.

    The output type is anything pydantic-ai accepts, usually a pydantic model: the model answers
    by filling its fields, and an answer that fails its validation is sent back to the model to
    be corrected before the call gives up. Use str for a plain text answer.

    Each call opens its own HTTP client and closes it before returning, so a client can be built
    per request and dropped without leaking connections.

    Example::

        class Summary(BaseModel):
            title: str = Field(description="标题")

        client = LLMClient(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=key))
        summary = await client.run("总结一下这段话：……", output_type=Summary)

    :param config: Where the calls go.
    :param timeout_seconds: Timeout of each model request.
    :param transport: httpx transport for the model's HTTP client; tests inject MockTransport.
    """

    def __init__(
        self,
        config: LLMConfig,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def run(
        self,
        prompt: str,
        *,
        output_type: type[OutputT],
        instructions: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking: ThinkingConfig | None = None,
    ) -> OutputT:
        """Send one user message and return the model's answer as output_type.

        :param prompt: The user message.
        :param output_type: What the answer is validated into.
        :param instructions: The system prompt; None for none.
        :param temperature: Sampling temperature; None for the model's default.
        :param max_tokens: Most tokens the answer may hold; None for the model's default.
        :param thinking: How much to think; None for the model's default.
        :return: The validated answer.
        :raises LLMConfigurationError: If the config names something that cannot be called.
        :raises LLMCallError: If the model was unreachable, refused the request, or kept
            answering with something that does not validate as output_type.
        """
        model_settings: ModelSettings = {"timeout": self._timeout_seconds}
        if temperature is not None:
            model_settings["temperature"] = temperature
        if max_tokens is not None:
            model_settings["max_tokens"] = max_tokens

        async with open_model(self._config, transport=self._transport) as model:
            capabilities = []
            if thinking is not None and (level := _resolve_thinking(thinking, model.profile)) is not None:
                capabilities.append(Thinking(effort=level))
            agent = Agent(model, instructions=instructions, output_type=output_type, capabilities=capabilities)
            try:
                result = await agent.run(prompt, model_settings=model_settings)
            except (AgentRunError, UserError) as exc:
                raise LLMCallError(_describe_failure(model.model_name, exc)) from exc
        return result.output


def _resolve_thinking(thinking: ThinkingConfig, profile: ModelProfile) -> ThinkingLevel | None:
    """Turn a ThinkingConfig into the thinking level to ask this model for, None to ask for none."""
    always_thinks = profile.get("thinking_always_enabled", False)
    if not always_thinks and not profile.get("supports_thinking", False):
        return None
    # 关不掉思考的模型，pydantic-ai 会把 False 换成它认为最低的强度，甚至什么都不发；这里换成调用方
    # 指定的强度，而不是由库替我们选。
    if thinking.enabled or always_thinks:
        return thinking.effort
    return False


def _describe_failure(model_name: str, exc: Exception) -> str:
    """Say which model failed and how, without the vendor's message or response body."""
    # 厂商的错误体格式不归我们管，不保证里面没有请求原文，所以只报异常类型和状态码。
    detail = type(exc).__name__
    if isinstance(exc, ModelHTTPError):
        detail = f"{detail}, HTTP {exc.status_code}"
    return f"Calling model {model_name!r} failed: {detail}"
