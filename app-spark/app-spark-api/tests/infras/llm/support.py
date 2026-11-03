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

"""Shared pieces for tests that call an LLM, offline or for real."""

from __future__ import annotations

import json
import os
from functools import partial
from typing import TYPE_CHECKING

import httpx2
import pytest

from app_spark_api.infras.llm import DirectLLMConfig, GatewayLLMConfig, LLMClient

if TYPE_CHECKING:
    from collections.abc import Callable

    from _pytest.mark import ParameterSet

    from app_spark_api.infras.llm import LLMConfig

# pydantic-ai 的结构化输出走一个工具调用，这是它默认给这个工具起的名字。
OUTPUT_TOOL_NAME = "final_result"

# 直连 DeepSeek：与 pydantic-ai 的 DeepSeekProvider 读的是同一个变量。
LIVE_DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
LIVE_DEEPSEEK_MODEL = os.environ.get("APP_SPARK_LIVE_LLM_MODEL", "deepseek:deepseek-v4-flash")

# bkaidev 网关：用户态 token 与 v1 地址，以及要测的模型 ID（逗号分隔）。
LIVE_BKAIDEV_ACCESS_TOKEN_ENV = "APP_SPARK_LIVE_BKAIDEV_ACCESS_TOKEN"
LIVE_BKAIDEV_BASE_URL_ENV = "APP_SPARK_LIVE_BKAIDEV_BASE_URL"
LIVE_BKAIDEV_MODEL_IDS_ENV = "APP_SPARK_LIVE_BKAIDEV_MODEL_IDS"
LIVE_BKAIDEV_DEFAULT_MODEL_IDS = "deepseek-v4-flash"


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _live_deepseek_config() -> LLMConfig:
    api_key = _env(LIVE_DEEPSEEK_API_KEY_ENV)
    if not api_key:
        pytest.skip(f"live DeepSeek tests need {LIVE_DEEPSEEK_API_KEY_ENV}")
    return DirectLLMConfig(model=LIVE_DEEPSEEK_MODEL, api_key=api_key)


def _live_bkaidev_config(model_id: str) -> LLMConfig:
    access_token, base_url = _env(LIVE_BKAIDEV_ACCESS_TOKEN_ENV), _env(LIVE_BKAIDEV_BASE_URL_ENV)
    if not access_token or not base_url:
        pytest.skip(f"live bkaidev tests need {LIVE_BKAIDEV_ACCESS_TOKEN_ENV} and {LIVE_BKAIDEV_BASE_URL_ENV}")
    return GatewayLLMConfig(base_url=base_url, access_token=access_token, model_id=model_id)


def _live_targets() -> list[ParameterSet]:
    """Every live target, one param each; a target whose credentials are missing skips itself."""
    # 参数在收集阶段就要定下来，所以模型清单只能在这里读环境变量；凭据留到用例真正运行时再查。
    model_ids = [m.strip() for m in (_env(LIVE_BKAIDEV_MODEL_IDS_ENV) or LIVE_BKAIDEV_DEFAULT_MODEL_IDS).split(",")]
    return [
        pytest.param(_live_deepseek_config, id="deepseek"),
        *(pytest.param(partial(_live_bkaidev_config, m), id=f"bkaidev-{m}") for m in model_ids if m),
    ]


@pytest.fixture(params=_live_targets())
def live_llm(request) -> LLMClient:
    """A client for one real model. Tests using it run once per live target and skip where unconfigured.

    These tests spend real money and time, so they also carry the live_llm marker.
    """
    return LLMClient(request.param())


def chat_completion(content: str, *, model: str = "test-model") -> dict:
    """An OpenAI Chat Completions answer with one assistant message."""
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1792662210,
        "model": model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"},
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def tool_call_completion(tool_name: str, arguments: dict) -> dict:
    """An OpenAI Chat Completions answer that calls one tool, the way structured output arrives."""
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(arguments, ensure_ascii=False)},
            }
        ],
    }
    answer = chat_completion("")
    answer["choices"] = [{"index": 0, "message": message, "finish_reason": "tool_calls"}]
    return answer


def answer_with_outputs(*outputs: dict) -> RecordingTransport:
    """A transport that answers each request with the next structured output, in order."""
    pending = list(outputs)
    return RecordingTransport(
        lambda _request: httpx2.Response(200, json=tool_call_completion(OUTPUT_TOOL_NAME, pending.pop(0)))
    )


class RecordingTransport(httpx2.MockTransport):
    """A MockTransport that remembers every request it answered."""

    def __init__(self, answer: Callable[[httpx2.Request], httpx2.Response]) -> None:
        self.requests: list[httpx2.Request] = []

        def handler(request: httpx2.Request) -> httpx2.Response:
            self.requests.append(request)
            return answer(request)

        super().__init__(handler)

    @property
    def last_body(self) -> dict:
        return json.loads(self.requests[-1].content)


def answer_with(content: str) -> RecordingTransport:
    """A transport whose every request is answered with the same assistant message."""
    return RecordingTransport(lambda _request: httpx2.Response(200, json=chat_completion(content)))
