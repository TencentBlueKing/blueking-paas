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

from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from django.conf import settings

from app_spark_api.agent.runtime.constants import ModelSource
from app_spark_api.agent.runtime.entities import (
    BkAidevModelAccess,
    structure_bkaidev_model_config,
    structure_direct_model_config,
)
from app_spark_api.agent.runtime.exceptions import (
    ModelAccessConfigurationError,
    ModelCredentialMissingError,
    ModelNotAvailableError,
)
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


def check_model_source_settings() -> None:
    """Refuse, at startup, a bkaidev model configuration that could never serve a model list.

    :raises ModelAccessConfigurationError: If BKAIDEV_MODEL_CONFIG is invalid while bkaidev is
        the model source.
    """
    # 只在 bkaidev 下校验：direct 部署用不到这份配置，不该因为它起不来。来源名本身写错时也放过，
    # 那会在第一次用到模型时报给运维，不属于这里要挡的东西。
    if settings.AGENT_MODEL_SOURCE != ModelSource.BKAIDEV:
        return

    structure_bkaidev_model_config(settings.BKAIDEV_MODEL_CONFIG)


def resolve_run_model_name(model_id: str | None) -> str | None:
    """Check the model a turn asked for and return the name to forward to the Runtime.

    Runs on every turn, so it only reads settings: no token exchange and no call upstream. The
    gateway still has the last word on a name that passes here, and refuses it inside the run.

    Example::

        model_name = resolve_run_model_name(payload.model_id)
        await client.start_run(content=content, context_version=version, model_name=model_name)

    :param model_id: The model the turn asked for, None when it asked for none.
    :return: The name to send as forwardedProps.modelName, or None to let the Runtime use its
        default model.
    :raises ModelNotAvailableError: If this deployment does not offer the model.
    :raises ModelAccessConfigurationError: If the model source or its settings are invalid.
    """
    # 没带模型就交给 Runtime 用沙箱默认模型，不必读任何配置。
    if model_id is None:
        return None

    # direct 只有一个内置模型，沙箱启动时已经定了，带了也不用转发。比对的 ID 和模型列表给前端的是同一个。
    if get_model_source() == ModelSource.DIRECT:
        builtin = structure_direct_model_config(settings.AGENT_DIRECT_MODEL_CONFIG).model_id
        if model_id != builtin:
            raise ModelNotAvailableError(f"Model {model_id!r} is not the built-in model {builtin!r}")

        return None

    # 可选列表为空时不收窄，名字原样交给网关裁决；非空时只放行能被某一项匹配上的，和模型列表用同一套
    # 匹配规则。模型列表在一项都没命中网关时会退回全部模型，这里不跟着放宽：那要先调网关才知道。
    config = structure_bkaidev_model_config(settings.BKAIDEV_MODEL_CONFIG)
    if config.available_models and not any(fnmatchcase(model_id, pattern) for pattern in config.available_models):
        raise ModelNotAvailableError(f"Model {model_id!r} matches nothing in BKAIDEV_MODEL_CONFIG.available_models")

    return model_id


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
        return structure_direct_model_config(settings.AGENT_DIRECT_MODEL_CONFIG).to_access()

    return await resolve_bkaidev_model_access(credential, transport=transport)


async def resolve_bkaidev_model_access(
    credential: UserCredential | None,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> BkAidevModelAccess:
    """Return the bkaidev gateway address, default model and this user's token.

    Shared by a Runtime about to start and by the model list, which calls the same gateway with
    the same token.

    :param credential: The user's BlueKing login, None when the request carried none.
    :param transport: httpx transport for the token service; tests inject MockTransport.
    :raises ModelAccessConfigurationError: If the bkaidev settings are invalid.
    :raises ModelCredentialMissingError: If the request has no login.
    :raises AccessTokenUnavailableError: If the token service could not give a token.
    """
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
