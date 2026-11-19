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

"""Where an LLM call goes, one config class per model source.

The three sources mirror the Agent's model modes: fake for tests, direct to a vendor with a fixed
key, and the bkaidev gateway with a user's access_token.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import attrs

from app_spark_api.utils.attrs import validate_non_empty_string

if TYPE_CHECKING:
    from pydantic_ai.settings import ThinkingEffort


@attrs.frozen
class FakeLLMConfig:
    """A model that makes no network request and gives the same answer to every call.

    :param output: The answer. A str for a text answer; for a structured output, the output
        model's fields, e.g. {"name": "番茄钟"}; None lets the fake make one up that fits the
        output type.
    """

    output: str | dict[str, Any] | None = None


@attrs.frozen
class DirectLLMConfig:
    """Call a model vendor directly with a fixed key.

    :param model: pydantic-ai model string, <provider>:<model>, e.g. deepseek:deepseek-v4-flash.
    :param api_key: The vendor's API key.
    """

    model: str = attrs.field(validator=validate_non_empty_string)
    api_key: str = attrs.field(validator=validate_non_empty_string, repr=False)

    @model.validator
    def _validate_model(self, attribute: attrs.Attribute[str], value: str) -> None:
        # 不带 provider 前缀时 pydantic-ai 会按模型名去猜厂商，猜错了 key 就发到了别家。
        provider, _, name = value.partition(":")
        if not provider or not name:
            raise ValueError(f"{attribute.name} must look like <provider>:<model>, got {value!r}")


@attrs.frozen
class GatewayLLMConfig:
    """Call a model through the bkaidev LLM gateway on one user's behalf.

    :param base_url: The gateway's OpenAI-compatible v1 root, without /chat/completions.
    :param access_token: The user's access_token for this service's app.
    :param model_id: The gateway's llm_code, without a vendor prefix, e.g. deepseek-v4-flash.
    """

    base_url: str = attrs.field(validator=validate_non_empty_string)
    access_token: str = attrs.field(validator=validate_non_empty_string, repr=False)
    model_id: str = attrs.field(validator=validate_non_empty_string)


LLMConfig = FakeLLMConfig | DirectLLMConfig | GatewayLLMConfig


@attrs.frozen
class ThinkingConfig:
    """How much one call should think, applied only as far as the model is known to support it.

    - A model not known to have a thinking setting is left at its default; nothing is sent.
    - enabled=True thinks at effort.
    - enabled=False turns thinking off; a model known to be unable to turn it off thinks at effort.

    :param enabled: Whether the call should think at all.
    :param effort: The effort used whenever the call does think.
    """

    enabled: bool
    effort: ThinkingEffort = "medium"
