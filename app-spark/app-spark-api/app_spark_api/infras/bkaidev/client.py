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

"""Calling the bkaidev LLM gateway as one user."""

from __future__ import annotations

import json

import httpx2

from app_spark_api.infras.bkaidev.entities import GatewayModel, structure_gateway_model_list
from app_spark_api.infras.bkaidev.exceptions import BkAidevGatewayError

# 蓝鲸网关的公共鉴权头，值是 JSON 字符串。只放用户态 access_token，不放 app_code / app_secret：
# 网关按「签发 token 的应用 + 用户」鉴权，和 Runtime 调推理接口时是同一张 token。
BKAPI_AUTHORIZATION_HEADER = "X-Bkapi-Authorization"


class BkAidevGatewayClient:
    """Ask the bkaidev LLM gateway what it offers, on one user's behalf.

    Example::

        client = BkAidevGatewayClient(base_url=access.base_url, access_token=access.access_token)
        models = await client.list_models()

    :param base_url: The gateway's OpenAI-compatible v1 root, as given to a Runtime.
    :param access_token: The user's access_token for this service's app.
    :param timeout_seconds: Timeout of each request.
    :param transport: httpx transport; tests inject MockTransport.
    """

    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        timeout_seconds: float = 10.0,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._access_token = access_token
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def list_models(self) -> list[GatewayModel]:
        """GET /models: the models the gateway lets this app call.

        :return: The readable models, in the gateway's order; unreadable cards are skipped.
        :raises BkAidevGatewayError: If the gateway was unreachable, answered non-2xx, or
            answered with a body that is not a model list.
        """
        url = f"{self._base_url}/models"
        async with httpx2.AsyncClient(timeout=self._timeout_seconds, transport=self._transport) as client:
            try:
                response = await client.get(url, headers=self._build_headers())
            except httpx2.HTTPError as exc:
                # 只带异常类型：httpx 的消息里可能带着请求细节，这里不冒把 token 写进日志的险。
                raise BkAidevGatewayError(f"Requesting {url} failed: {type(exc).__name__}") from exc

        # 只报状态码，不回显响应体：网关的错误体格式不归我们管，不保证里面没有请求原文。
        if not response.is_success:
            raise BkAidevGatewayError(f"{url} answered HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise BkAidevGatewayError(f"{url} answered with a body that is not JSON") from exc

        return structure_gateway_model_list(payload)

    def _build_headers(self) -> dict[str, str]:
        """Build the headers every gateway request carries."""
        return {BKAPI_AUTHORIZATION_HEADER: json.dumps({"access_token": self._access_token}, separators=(",", ":"))}
