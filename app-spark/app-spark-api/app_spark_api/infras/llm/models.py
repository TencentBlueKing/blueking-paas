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

"""Turning an LLMConfig into a pydantic-ai model whose HTTP client is closed after use."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING, Any, Protocol, cast

import httpx2
from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from pydantic_ai.models import infer_model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.profiles import merge_profile
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers import Provider, infer_provider_class
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.vllm import VLLMProvider

from app_spark_api.infras.bkaidev import build_authorization_headers
from app_spark_api.infras.llm.entities import DirectLLMConfig, FakeLLMConfig, GatewayLLMConfig
from app_spark_api.infras.llm.exceptions import LLMConfigurationError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from pydantic_ai.models import Model
    from pydantic_ai.profiles import ModelProfile
    from pydantic_ai.profiles.openai import OpenAIReasoningEffort

    from app_spark_api.infras.llm.entities import LLMConfig

# OpenAI SDK 构造客户端时必须有 api_key，网关不认它，真正的鉴权在 X-Bkapi-Authorization 里。
_GATEWAY_API_KEY_PLACEHOLDER = "empty"

# 网关下的模型 ID 不归 OpenAI 命名，不能交给 pydantic-ai 按名字推断能力档：deepseek-v4.1-flash
# 会因为名字里有 4.1 被套上 gpt-4.1 的规则。和 Agent 一样钉死成「OpenAI 兼容通用档 + 工具与
# 结构化输出全开」。这份档不声明 thinking，所以默认不发任何 thinking 参数。
_GATEWAY_PROFILE = merge_profile(
    OpenAIProvider.model_profile("") or {},
    OpenAIModelProfile(
        supports_tools=True,
        supports_json_schema_output=True,
        supports_json_object_output=True,
        supports_tool_return_schema=True,
    ),
)


def _measured_thinking(efforts: frozenset[OpenAIReasoningEffort]) -> Callable[[str], ModelProfile]:
    """A thinking profile written from our own measurement, for a model pydantic-ai has no profile for.

    :param efforts: The reasoning_effort values the gateway was seen to accept for the model.
        Only these are ever sent; a requested level outside them goes to the nearest one. Without
        none the model counts as unable to turn thinking off.
    """
    profile = OpenAIModelProfile(
        supports_thinking=True,
        thinking_always_enabled="none" not in efforts,
        openai_reasoning_efforts=efforts,
    )
    return lambda _model_id: profile


# 混元默认要思考，用掉几十个 completion token，多数型号不回传思考内容（hy4 回传）；none 能关掉
# （只剩答案的 2 个 token）。其它强度都接受，但用量看不出差别。
_HUNYUAN_THINKING = _measured_thinking(frozenset({"none", "minimal", "low", "medium", "high", "xhigh", "max"}))

# thinking 白名单，人工维护，增改的步骤见 docs/misc.md「为网关模型适配 thinking」。
#
# 网关模型 ID（fnmatch，区分大小写，按顺序先匹配先用）→ 它的 thinking 档从哪来：
# - pydantic-ai 自带的厂商档：只借其中和 thinking 有关的字段，怎么开关、发什么取值由 pydantic-ai 维护；
# - _measured_thinking(...)：pydantic-ai 没有对应的档时，按我们对网关的实测写；
# - None：显式排除。
# 匹配不上或为 None 的模型不发 thinking 参数，请求不会因为取值不被接受而失败。
#
# 2026-11-03 对照网关实测选的，qwen3 系列与 hy4、hy4-preview 2026-11-05 复测。没列的模型及原因：
# - GLM：上游的开关做在 ZaiModel 里、用 thinking.type，网关对它返回 400；
# - kimi、qwen3-8b：网关接受 none 但照样思考，关不掉也不会退到指定强度；
# - qwen3-235B、qwen3-5-397B：不认 high（只认 low / medium / xhigh），上游会把 high 原样发出去换来 400；
# - qwen3-nothinking：medium 及以上返回 400；qwen3-5-27B-nothinking：从不思考，发了也没用；
# - gpt-oss：上游档不声明 thinking，借了也没用；
# - SRE、aidev-*、dsv32*：没测过。
# deepseek-v4.1-flash、deepseek-chat、deepseek-v3 虽然匹配 deepseek-*，但上游档不认为它们能设 thinking，
# 同样不发。qwen3 系列各型号行为不一，只按 ID 逐个收录，不用通配符。
_GATEWAY_THINKING_PROFILES: dict[str, Callable[[str], ModelProfile | None] | None] = {
    "deepseek-*": DeepSeekProvider.model_profile,
    # 网关上的 qwen 是自部署的，按 vLLM 的档走：用 reasoning_effort 开关思考，none 能关掉。
    "qwen3": VLLMProvider.model_profile,
    "qwen3-5-27B": VLLMProvider.model_profile,
    # 混元的 vision 和 embedding 模型没测，不收录。
    "hy3*": _HUNYUAN_THINKING,
    "hy4*": _HUNYUAN_THINKING,
    "hunyuan": _HUNYUAN_THINKING,
    "hunyuan-13B": _HUNYUAN_THINKING,
    "hunyuan-turbos": _HUNYUAN_THINKING,
}


def gateway_model_profile(model_id: str) -> ModelProfile:
    """Return the fixed capability profile of one gateway model.

    Thinking is declared only for models matched by the thinking whitelist; any other model gets
    no thinking parameter at all.

    :param model_id: The gateway's llm_code.
    """
    for pattern, upstream_profile in _GATEWAY_THINKING_PROFILES.items():
        if fnmatchcase(model_id, pattern):
            if upstream_profile is None:
                break
            upstream = upstream_profile(model_id) or {}
            thinking = {key: value for key, value in upstream.items() if "thinking" in key or "reasoning" in key}
            return merge_profile(_GATEWAY_PROFILE, cast("ModelProfile", thinking))
    return _GATEWAY_PROFILE


class _ApiKeyProvider(Protocol):
    """A provider class that authenticates with a plain API key."""

    def __call__(self, *, api_key: str, http_client: httpx2.AsyncClient | None = None) -> Provider[Any]: ...


@asynccontextmanager
async def open_model(config: LLMConfig, *, transport: httpx2.AsyncBaseTransport | None = None) -> AsyncIterator[Model]:
    """Build the model a config points at, and close its HTTP client on exit.

    Example::

        async with open_model(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key=key)) as model:
            result = await Agent(model).run("hello")

    :param config: Where the calls go.
    :param transport: httpx transport for the model's HTTP client; tests inject MockTransport.
    :raises LLMConfigurationError: If a direct config names a provider pydantic-ai does not know.
    """
    match config:
        case FakeLLMConfig():
            yield _build_fake_model(config)
        case DirectLLMConfig():
            async with _open_direct_model(config, transport=transport) as model:
                yield model
        case GatewayLLMConfig():
            async with _open_gateway_model(config, transport=transport) as model:
                yield model


def _build_fake_model(config: FakeLLMConfig) -> TestModel:
    """Answer with the configured output, never with a tool call of the caller's own."""
    if isinstance(config.output, str):
        return TestModel(custom_output_text=config.output, call_tools=[], model_name="fake")
    return TestModel(custom_output_args=config.output, call_tools=[], model_name="fake")


@asynccontextmanager
async def _open_direct_model(
    config: DirectLLMConfig, *, transport: httpx2.AsyncBaseTransport | None
) -> AsyncIterator[Model]:
    """Call the vendor named by the model string, authenticating with the fixed key."""
    provider_name = config.model.partition(":")[0]
    try:
        provider_class = cast("_ApiKeyProvider", infer_provider_class(provider_name))
    except ValueError as exc:
        raise LLMConfigurationError(f"Unknown model provider: {provider_name!r}") from exc

    if transport is None:
        # 不传 http_client 时客户端归 provider 所有，进出 model 的上下文就会把它关掉。
        provider = provider_class(api_key=config.api_key)
        model = infer_model(config.model, provider_factory=lambda _name: provider)
        async with model:
            yield model
        return

    async with httpx2.AsyncClient(transport=transport) as http_client:
        provider = provider_class(api_key=config.api_key, http_client=http_client)
        yield infer_model(config.model, provider_factory=lambda _name: provider)


@asynccontextmanager
async def _open_gateway_model(
    config: GatewayLLMConfig, *, transport: httpx2.AsyncBaseTransport | None
) -> AsyncIterator[Model]:
    """Call the gateway's Chat Completions with the user's token, never with a Bearer key."""
    client = AsyncOpenAI(
        base_url=config.base_url,
        api_key=_GATEWAY_API_KEY_PLACEHOLDER,
        default_headers=build_authorization_headers(config.access_token),
        http_client=DefaultAsyncHttpxClient(transport=_WithoutAuthorization(transport)),
    )
    async with client:
        yield OpenAIChatModel(
            config.model_id,
            provider=OpenAIProvider(openai_client=client),
            profile=_pin_profile(gateway_model_profile(config.model_id)),
        )


class _WithoutAuthorization(httpx2.AsyncBaseTransport):
    """Drop the Authorization: Bearer <placeholder> the OpenAI SDK adds to every request.

    The SDK refuses to send a request without either an api_key or that header, so the gateway
    client is built with a placeholder key, and the header it produces is removed here, leaving
    X-Bkapi-Authorization as the only credential that goes out.
    """

    def __init__(self, wrapped: httpx2.AsyncBaseTransport | None = None) -> None:
        self._wrapped = wrapped or httpx2.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        request.headers.pop("Authorization", None)
        return await self._wrapped.handle_async_request(request)

    async def aclose(self) -> None:
        await self._wrapped.aclose()


def _pin_profile(profile: ModelProfile) -> Callable[[ModelProfile], ModelProfile]:
    """Wrap a profile as a function, so it replaces the inferred one instead of merging into it."""

    def replace(_inferred: ModelProfile) -> ModelProfile:
        return profile

    return replace
