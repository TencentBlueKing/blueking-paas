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

"""Deciding how a new Agent Runtime calls its model, and getting it a token when that is bkaidev."""

from typing import TYPE_CHECKING

from django.conf import settings

from app_spark_api.agent.runtime.constants import ModelSource
from app_spark_api.agent.runtime.entities import (
    BkAidevModelAccess,
    structure_bkaidev_model_config,
    structure_direct_model_config,
)
from app_spark_api.agent.runtime.exceptions import ModelAccessConfigurationError, ModelCredentialMissingError
from app_spark_api.infras.bk_access_token import AccessTokenBackendConfig, get_access_token_backend_cls

if TYPE_CHECKING:
    import httpx2

    from app_spark_api.agent.runtime.entities import ModelAccess
    from app_spark_api.infras.bk_access_token import UserCredential


def get_model_source() -> ModelSource:
    """Return where this service's Agent Runtimes send their model calls.

    :raises ModelAccessConfigurationError: If AGENT_MODEL_SOURCE is not a known source.
    """
    try:
        return ModelSource(settings.AGENT_MODEL_SOURCE)
    except ValueError as exc:
        raise ModelAccessConfigurationError(f"Unknown AGENT_MODEL_SOURCE: {settings.AGENT_MODEL_SOURCE!r}") from exc


def _require_setting(name: str, value: object) -> str:
    """Return a non-empty settings string, or say which top-level key the operator must set."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise ModelAccessConfigurationError(f"{name} is required for bkaidev model access")
    return text


def build_bkaidev_llm_base_url() -> str:
    """Return the bkaidev OpenAI-compatible v1 root injected as MODEL_BASE_URL."""
    tmpl = _require_setting("BK_API_URL_TMPL", settings.BK_API_URL_TMPL)
    stage = _require_setting("APIGW_ENVIRONMENT", settings.APIGW_ENVIRONMENT)

    # format 遇到没用上的关键字参数不会报错：模板里没有 {api_name} 时会原样返回，拼出一个少了
    # 网关名的地址，用户的 token 就被发到了错误的路径。所以先显式检查。
    if "{api_name}" not in tmpl:
        raise ModelAccessConfigurationError(f"BK_API_URL_TMPL must contain {{api_name}}: {tmpl!r}")

    # 除 {api_name} 之外的占位符或残缺的花括号，format 会抛这几种异常。
    try:
        root = tmpl.format(api_name="bkaidev").rstrip("/")
    except (KeyError, IndexError, ValueError) as exc:
        raise ModelAccessConfigurationError(
            f"BK_API_URL_TMPL may contain no placeholder other than {{api_name}}: {tmpl!r}"
        ) from exc

    # 停在 v1 这一层，不要带 /chat/completions，agent 会自己拼。
    return f"{root}/{stage}/openapi/aidev/gateway/llm/v1"


def build_access_token_backend_config() -> AccessTokenBackendConfig:
    """Build the token-exchange config from top-level settings."""
    # 换票支持直连 auth api 或 SSM 两种 backend，地址不从 BK_API_URL_TMPL 拼，由部署方填。
    # env_name 只有 AuthApiBackend 会发；配成空时按 prod 处理，不因为一个用不上的字段拦下 SSM 换票。
    return AccessTokenBackendConfig(
        token_url=_require_setting("TOKEN_AUTH_ENDPOINT", settings.TOKEN_AUTH_ENDPOINT),
        app_code=_require_setting("APP_CODE", settings.APP_CODE),
        app_secret=_require_setting("APP_SECRET", settings.APP_SECRET),
        env_name=str(settings.AUTH_ENV_NAME or "").strip() or "prod",
    )


async def resolve_model_access(
    credential: UserCredential | None,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> ModelAccess:
    """Return what a Runtime about to be started needs to call its model as this user.

    Meant to be handed to a provider as a ModelAccessResolver, so it runs only when a Runtime is
    really being started. Asks the token service every time and keeps nothing: the token service
    hands back the user's current token instead of issuing a new one, so there is no local copy
    to store, expire, or leak.

    Example::

        credential = get_user_credential(request)
        await provider.ensure(..., model_access=lambda: resolve_model_access(credential))

    :param credential: The user's BlueKing login, None when the request carried none.
    :param transport: httpx transport for the token service; tests inject MockTransport.
    :return: The fixed vendor model and key for direct calls, or the bkaidev address, model and
        the user's token.
    :raises ModelAccessConfigurationError: If the model source or its settings are invalid.
    :raises ModelCredentialMissingError: If bkaidev is used and the request has no login.
    :raises AccessTokenUnavailableError: If the token service could not give a token.
    """
    if get_model_source() == ModelSource.DIRECT:
        return structure_direct_model_config(settings.AGENT_DIRECT_MODEL_CONFIG)

    # 先校验配置再看登录态：配置缺失是运维问题，不该让用户误以为重新登录就能解决。
    config = structure_bkaidev_model_config(settings.BKAIDEV_MODEL_CONFIG)
    token_backend_config = build_access_token_backend_config()
    base_url = build_bkaidev_llm_base_url()

    if credential is None:
        raise ModelCredentialMissingError("Calling bkaidev needs the user's BlueKing login, and the request has none")

    backend = get_access_token_backend_cls()(token_backend_config, transport=transport)
    access_token = await backend.fetch_user_token(credential)
    return BkAidevModelAccess(
        base_url=base_url,
        access_token=access_token,
        model_name=config.default_model_name,
    )
