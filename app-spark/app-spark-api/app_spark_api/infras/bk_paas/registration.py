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

"""Best-effort registration of the current user in the developer center."""

import asyncio
import logging
from typing import TYPE_CHECKING

from django.conf import settings

from app_spark_api.infras.accounts.auth import authenticated_user
from app_spark_api.infras.accounts.credentials import get_user_credential
from app_spark_api.infras.bk_access_token import AccessTokenBackendConfig, get_access_token_backend_cls
from app_spark_api.infras.bk_paas.client import BkPaaSClient
from app_spark_api.infras.bk_paas.exceptions import BkPaaSConfigurationError

if TYPE_CHECKING:
    import httpx2
    from django.http import HttpRequest

    from app_spark_api.infras.bk_access_token import UserCredential

logger = logging.getLogger(__name__)

# 换票和注册加在一起的上限。建项目的人要等它结束，失败不能拖太久；成功时两次请求都远快于这个上限。
REGISTER_TIMEOUT_SECONDS = 5.0


async def aregister_user_profile(
    request: HttpRequest,
    *,
    token_transport: httpx2.AsyncBaseTransport | None = None,
    paas_transport: httpx2.AsyncBaseTransport | None = None,
) -> None:
    """Register the current user in the developer center, ignoring any failure.

    :param request: 建项目的请求，登录态从这里取。
    :param token_transport: 换票请求的 httpx transport，测试注入。
    :param paas_transport: 开发者中心请求的 httpx transport，测试注入。
    """

    credential = get_user_credential(request)

    # 没有蓝鲸登录态就换不出用户 token，注册接口也不知道是谁。
    if credential is None:
        logger.warning(
            "Skip registering user %s in the developer center: the request carries no BlueKing login",
            authenticated_user(request).username,
        )
        return

    try:
        async with asyncio.timeout(REGISTER_TIMEOUT_SECONDS):
            await _register(credential, token_transport=token_transport, paas_transport=paas_transport)
    except Exception:
        # 建项目不依赖这次注册。超时、换票失败、开发者中心拒绝都留在日志里，等人要发布时再处理。
        logger.exception("Registering user %s in the developer center failed", credential.username)


async def _register(
    credential: UserCredential,
    *,
    token_transport: httpx2.AsyncBaseTransport | None,
    paas_transport: httpx2.AsyncBaseTransport | None,
) -> None:
    """Exchange the user's login for an access_token and register that user."""

    config = _build_token_config()
    backend = get_access_token_backend_cls()(config, transport=token_transport)
    access_token = await backend.fetch_user_token(credential)

    # 地址和发布走同一套网关配置。外层 asyncio.timeout 会在 5 秒时取消，这里不再单独缩短客户端超时。
    async with BkPaaSClient.from_settings(transport=paas_transport) as client:
        await client.register_user_profile(access_token)


def _build_token_config() -> AccessTokenBackendConfig:
    """Build the token-exchange config, capped by the registration budget."""

    # env_name 只有走 auth api 换票时才会发出去；配成空时按 prod 处理，不因为一个用不上的字段拦下 bk_token。
    return AccessTokenBackendConfig(
        token_url=_require_setting("TOKEN_AUTH_ENDPOINT", settings.TOKEN_AUTH_ENDPOINT),
        app_code=_require_setting("APP_CODE", settings.APP_CODE),
        app_secret=_require_setting("APP_SECRET", settings.APP_SECRET),
        env_name=str(settings.AUTH_ENV_NAME or "").strip() or "prod",
        timeout_seconds=REGISTER_TIMEOUT_SECONDS,
    )


def _require_setting(name: str, value: object) -> str:
    """Return a non-empty settings string, or say which key is missing."""

    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise BkPaaSConfigurationError(f"{name} is required to register a user in the developer center")

    return text
