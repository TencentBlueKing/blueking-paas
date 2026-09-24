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

"""Exchanging a user's BlueKing login for a user-scoped access_token."""

from typing import Any

import httpx2

from app_spark_api.infras.bk_access_token.entities import AccessTokenClientConfig, UserCredential, UserCredentialType
from app_spark_api.infras.bk_access_token.exceptions import AccessTokenUnavailableError


class AccessTokenClient:
    """Ask the token service for the access_token binding one app to one user.

    The request body follows blueking-paas apiserver's APIGateWayBackend and BKSSMBackend, plus
    need_new_token=0 on both, so asking again returns the token a running Runtime already holds.

    Example::

        client = AccessTokenClient(config)
        token = await client.fetch_user_token(
            UserCredential(type=UserCredentialType.BK_TOKEN, value="...", username="admin")
        )

    :param config: The app identity and where the token service is.
    :param transport: httpx transport; tests inject MockTransport.
    """

    def __init__(self, config: AccessTokenClientConfig, *, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        self._config = config
        self._transport = transport

    async def fetch_user_token(self, credential: UserCredential) -> str:
        """Return the user's access_token for the configured app.

        :param credential: The logged-in user's BlueKing login.
        :return: The access_token.
        :raises AccessTokenUnavailableError: The token service was unreachable, refused the
            exchange, or answered without a token.
        """
        async with httpx2.AsyncClient(timeout=self._config.timeout_seconds, transport=self._transport) as client:
            try:
                response = await client.post(
                    self._config.token_url,
                    json=self._build_payload(credential),
                    headers={"X-BK-APP-CODE": self._config.app_code, "X-BK-APP-SECRET": self._config.app_secret},
                )
            except httpx2.HTTPError as exc:
                # 只带异常类型：httpx 的消息里可能带着请求 URL 之外的东西，这里不冒这个险。
                raise AccessTokenUnavailableError(
                    f"Requesting an access_token from {self._config.token_url} failed: {type(exc).__name__}"
                ) from exc

        return self._extract_token(response)

    def _build_payload(self, credential: UserCredential) -> dict[str, Any]:
        """Build the exchange request body for the kind of login the user has."""
        payload: dict[str, Any] = {
            "app_code": self._config.app_code,
            "app_secret": self._config.app_secret,
            "env_name": self._config.env_name,
            "grant_type": "authorization_code",
            credential.type.value: credential.value,
            # 两种登录都带：现有 token 仍有效、且剩余有效期大于 300 秒时原样返回，不重新签发。
            # 签发新 token 会让旧的失效，而 token 要在 Runtime 里一直用到会话结束，每次拉起都签
            # 新的，会把同一用户已经在跑的 Runtime 手里的 token 一起废掉。apiserver 的
            # BKSSMBackend 不带它，是因为那边的 token 只交给当次调用方，没有别人还拿着旧的。
            "need_new_token": 0,
        }

        # SSM 登录：由 bk_login 认证 bk_token，与 apiserver 的 BKSSMBackend 一致。
        if credential.type == UserCredentialType.BK_TOKEN:
            payload["id_provider"] = "bk_login"
            return payload

        # 网关登录：还要带用户名，与 apiserver 的 APIGateWayBackend 一致。
        payload["rtx"] = credential.username
        return payload

    def _extract_token(self, response: httpx2.Response) -> str:
        """Pull the access_token out of a token service response."""
        # 失败时只报状态码，不回显响应体：错误体里可能原样带着请求参数（含 app_secret）。
        if not response.is_success:
            raise AccessTokenUnavailableError(
                f"The token service refused the access_token exchange with HTTP {response.status_code}"
            )

        try:
            data = response.json().get("data")
        except ValueError, AttributeError:
            raise AccessTokenUnavailableError("The token service answered with a body that is not a JSON object")

        # 与 apiserver 的 validate_response 相同：data 为空视为换票失败，而不是拿空 token 去拉起 Runtime。
        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token:
            raise AccessTokenUnavailableError("The token service answered without an access_token")
        return token
