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

"""Exchanging a user's BlueKing login for a user-scoped access_token.

Supports two backends, calling auth api or SSM directly. BKAUTH_BACKEND_TYPE picks one.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx2
from django.conf import settings

from app_spark_api.infras.bk_access_token.entities import (
    AccessTokenBackendConfig,
    UserCredential,
    UserCredentialType,
)
from app_spark_api.infras.bk_access_token.exceptions import AccessTokenUnavailableError


class AccessTokenBackend(ABC):
    """Ask the token service for the access_token binding one app to one user.

    Example::

        backend = get_access_token_backend_cls()(config)
        token = await backend.fetch_user_token(credential)

    :param config: The app identity and where the token service is.
    :param transport: httpx transport; tests inject MockTransport.
    """

    # 这个 backend 认的登录态 cookie；读请求时按它取，换票时按它放进请求体。
    credential_type: ClassVar[UserCredentialType]

    def __init__(
        self, config: AccessTokenBackendConfig, *, transport: httpx2.AsyncBaseTransport | None = None
    ) -> None:
        self._config = config
        self._transport = transport

    async def fetch_user_token(self, credential: UserCredential) -> str:
        """Return the user's access_token for the configured app.

        :param credential: The logged-in user's BlueKing login.
        :return: The access_token.
        :raises AccessTokenUnavailableError: The token service was unreachable, refused the
            exchange, or answered without a token.
        """
        # 登录态种类和签发服务对不上时，请求发出去也只会被拒，还可能把登录态送到不认它的服务。
        if credential.type != self.credential_type:
            raise AccessTokenUnavailableError(
                f"{type(self).__name__} exchanges a {self.credential_type} login, got a {credential.type} one"
            )

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

    @abstractmethod
    def _build_payload(self, credential: UserCredential) -> dict[str, Any]:
        """Build the exchange request body this token service expects."""

    def _extract_token(self, response: httpx2.Response) -> str:
        """Pull the access_token out of a token service response."""
        # 失败时只报状态码，不回显响应体：错误体里可能原样带着请求参数（含 app_secret）。
        if not response.is_success:
            raise AccessTokenUnavailableError(
                f"The token service refused the access_token exchange with HTTP {response.status_code}"
            )

        # ValueError：正文不是 JSON；AttributeError：是 JSON 但不是 mapping（.get 不存在）。
        try:
            data = response.json().get("data")
        except ValueError, AttributeError:
            raise AccessTokenUnavailableError("The token service answered with a body that is not a JSON mapping")

        # 两个 backend 的 code 一个是字符串 "0"、一个是整数 0，但成功时都把 token 放在 data.access_token，
        # 所以只认 data。失败时 data 为空，视为换票失败。
        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token:
            raise AccessTokenUnavailableError("The token service answered without an access_token")
        return token


class AuthApiBackend(AccessTokenBackend):
    """Exchange a bk_ticket login with auth api."""

    credential_type = UserCredentialType.BK_TICKET

    def _build_payload(self, credential: UserCredential) -> dict[str, Any]:
        """Build the body carrying the app identity, env_name and rtx alongside bk_ticket."""
        return {
            "app_code": self._config.app_code,
            "app_secret": self._config.app_secret,
            "env_name": self._config.env_name,
            "grant_type": "authorization_code",
            "rtx": credential.username,
            "bk_ticket": credential.value,
            # 这个接口默认每次都签发新 token，并让旧的立即失效。token 要在 Runtime 里一直用到会话
            # 结束，不带这个参数，新开一个会话就会把同一用户已在跑的 Runtime 手里的 token 废掉。
            # 带上后，现有 token 仍有效且剩余超过 300 秒时原样返回。
            "need_new_token": 0,
        }


class SsmBackend(AccessTokenBackend):
    """Exchange a bk_token login with SSM."""

    credential_type = UserCredentialType.BK_TOKEN

    def _build_payload(self, credential: UserCredential) -> dict[str, Any]:
        """Build the body; the app identity travels in the X-BK-APP-* headers only."""
        # 这个签发接口本身是 create-or-update：同一应用同一用户已有未过期的 token 时直接返回
        # 原 token，所以不需要 need_new_token，接口也没有这个参数。
        return {
            "grant_type": "authorization_code",
            "id_provider": "bk_login",
            "bk_token": credential.value,
        }


def get_access_token_backend_cls() -> type[AccessTokenBackend]:
    """Return the backend matching this site's BKAUTH_BACKEND_TYPE."""
    # 只有 bk_token 用 SsmBackend，其余取值都用 AuthApiBackend。
    if settings.BKAUTH_BACKEND_TYPE == "bk_token":
        return SsmBackend
    return AuthApiBackend
