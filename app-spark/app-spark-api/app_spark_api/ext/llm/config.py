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

"""按 settings 里的 LLM_* 构造本服务自己调模型用的配置和客户端。

与 Agent Runtime 的模型来源分开配置，但 bkaidev 的网关基址与换票方式和它共用一套，见
agent.runtime.model_access。
"""

from __future__ import annotations

from enum import StrEnum

from django.conf import settings

from app_spark_api.agent.runtime.exceptions import ModelAccessConfigurationError
from app_spark_api.agent.runtime.model_access import build_bkaidev_llm_base_url
from app_spark_api.infras.llm import (
    DirectLLMConfig,
    FakeLLMConfig,
    GatewayLLMConfig,
    LLMClient,
    LLMConfig,
    LLMConfigurationError,
)
from app_spark_api.utils.attrs import structure_config


class LLMSource(StrEnum):
    """本服务调模型走哪条路，即 LLM_SOURCE 的可选值。"""

    # bkaidev 的 OpenAI 兼容 LLM 网关，凭用户态 access_token 调用。
    BKAIDEV = "bkaidev"
    # 直连模型厂商，用 LLM_DIRECT_CONFIG 里固定的 key。
    DIRECT = "direct"
    # 不发起网络请求的假模型。
    FAKE = "fake"


def get_llm_source() -> LLMSource:
    """返回 LLM_SOURCE 配置的来源。

    :raises LLMConfigurationError: LLM_SOURCE 不是已知的来源。
    """
    try:
        return LLMSource(settings.LLM_SOURCE)
    except ValueError as exc:
        raise LLMConfigurationError(f"Unknown LLM_SOURCE: {settings.LLM_SOURCE!r}") from exc


def requires_access_token() -> bool:
    """调模型是否需要用户态 access_token。

    为真时，调用方要在还有用户态的请求里用 fetch_bkaidev_access_token 先换好 token，再把它交给
    后台任务；后台任务里没有用户登录态，换不了。

    :raises LLMConfigurationError: LLM_SOURCE 不是已知的来源。
    """
    return get_llm_source() == LLMSource.BKAIDEV


def get_llm_config(*, access_token: str | None = None) -> LLMConfig:
    """按 settings 构造本服务调模型的配置。

    :param access_token: 用户态 access_token，LLM_SOURCE 为 bkaidev 时必填，其它来源忽略。
    :raises LLMConfigurationError: LLM_* 配置不完整或不合法。
    :raises ValueError: LLM_SOURCE 为 bkaidev，却没有给 access_token。这是调用方的问题：应该先用
        requires_access_token 判断，再在有用户态时换好 token。
    """
    match get_llm_source():
        case LLMSource.FAKE:
            return FakeLLMConfig()
        case LLMSource.DIRECT:
            return structure_config(settings.LLM_DIRECT_CONFIG, DirectLLMConfig, error_cls=LLMConfigurationError)
        case LLMSource.BKAIDEV:
            if not access_token:
                raise ValueError("LLM_SOURCE is bkaidev, calling a model needs the user's access_token")
            try:
                base_url = build_bkaidev_llm_base_url()
            except ModelAccessConfigurationError as exc:
                raise LLMConfigurationError(str(exc)) from exc
            return structure_config(
                {"base_url": base_url, "access_token": access_token, "model_id": settings.LLM_BKAIDEV_MODEL_ID},
                GatewayLLMConfig,
                error_cls=LLMConfigurationError,
            )


def build_llm_client(*, access_token: str | None = None) -> LLMClient:
    """按 settings 构造本服务调模型用的客户端。

    Example::

        # 在有用户态的请求里
        token = await fetch_bkaidev_access_token(credential) if requires_access_token() else None
        # 在后台任务里
        name = await generate_project_name(prompt, llm=build_llm_client(access_token=token))

    :param access_token: 用户态 access_token，LLM_SOURCE 为 bkaidev 时必填。
    :raises LLMConfigurationError: LLM_* 配置不完整或不合法。
    :raises ValueError: LLM_SOURCE 为 bkaidev，却没有给 access_token。
    """
    return LLMClient(get_llm_config(access_token=access_token), timeout_seconds=float(settings.LLM_TIMEOUT_SECONDS))
