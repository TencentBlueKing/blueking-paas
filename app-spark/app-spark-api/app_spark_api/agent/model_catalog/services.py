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

"""Working out which models a user may pick, from the gateway or from the fixed configuration."""

from __future__ import annotations

import logging
import time
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

import attrs
from django.conf import settings

from app_spark_api.agent.runtime.constants import ModelSource
from app_spark_api.agent.runtime.entities import structure_bkaidev_model_config, structure_direct_model_config
from app_spark_api.agent.runtime.exceptions import ModelCredentialMissingError
from app_spark_api.agent.runtime.model_access import (
    build_bkaidev_llm_base_url,
    get_model_source,
    resolve_bkaidev_model_access,
)
from app_spark_api.infras.bkaidev import BkAidevGatewayClient

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx2

    from app_spark_api.agent.runtime.entities import BkAidevModelConfig, DirectModelConfig
    from app_spark_api.infras.bk_access_token import UserCredential
    from app_spark_api.infras.bkaidev import GatewayModel

logger = logging.getLogger(__name__)

# 网关在新开通、下线模型后，最迟这么久之后列表里才能看到变化。
GATEWAY_MODELS_CACHE_SECONDS = 300.0


@attrs.frozen
class ModelOption:
    """一个可选模型。

    :param id: 模型 ID。
    :param name: 展示名称。
    :param context_window: 上下文窗口。
    :param supports_vision: 是否支持图像输入。
    """

    id: str
    name: str
    context_window: int | None = None
    supports_vision: bool = False


@attrs.frozen
class ModelCatalog:
    """当前部署可选的模型。

    :param source: 模型来源。
    :param allow_user_switch: 平台是否允许用户在会话中切换模型。
    :param default_model_id: 用户不选时使用的模型 ID。
    :param models: 可选模型。
    """

    source: ModelSource
    allow_user_switch: bool
    default_model_id: str
    models: list[ModelOption]


class GatewayModelsCache:
    """Keep the gateway's model list for a while, shared by every user of the same app.

    Example::

        cache = GatewayModelsCache(ttl_seconds=60)
        if (models := cache.get(key)) is None:
            models = await client.list_models()
            cache.put(key, models)

    :param ttl_seconds: How long a fetched list is served before the gateway is asked again.
    :param clock: Monotonic clock in seconds; tests inject a fake one.
    """

    def __init__(
        self,
        ttl_seconds: float = GATEWAY_MODELS_CACHE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[tuple[str, str], tuple[float, tuple[GatewayModel, ...]]] = {}

    def get(self, key: tuple[str, str]) -> list[GatewayModel] | None:
        """Return the list cached under key, or None when there is none or it has expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None

        expires_at, models = entry
        if self._clock() >= expires_at:
            return None

        return list(models)

    def put(self, key: tuple[str, str], models: list[GatewayModel]) -> None:
        """Cache models under key for the configured time."""
        self._entries[key] = (self._clock() + self._ttl_seconds, tuple(models))

    def clear(self) -> None:
        """Forget every cached list."""
        self._entries.clear()


# 只在进程内缓存：每个 worker 各自多问一次网关无妨，换来不依赖外部缓存服务。
# 缓存冷的时候并发请求会各自去取，同样无妨，不值得为此加锁。
gateway_models_cache = GatewayModelsCache()


async def list_models(
    credential: UserCredential | None,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> ModelCatalog:
    """Return the models this user may pick from, and the one a turn that picks none runs on.

    Example::

        catalog = await list_models(get_user_credential(request))

    :param credential: The user's BlueKing login, None when the request carried none.
    :param transport: httpx transport for the token service and the gateway; tests inject
        MockTransport.
    :raises ModelAccessConfigurationError: If the model source or its settings are invalid.
    :raises ModelCredentialMissingError: If bkaidev is used and the request has no login.
    :raises AccessTokenUnavailableError: If the token service could not give a token.
    :raises BkAidevGatewayError: If the gateway could not give its model list.
    """
    # direct 只有一个内置模型，不换票、不访问网络，读配置就够了。
    if get_model_source() == ModelSource.DIRECT:
        return _build_direct_catalog(structure_direct_model_config(settings.AGENT_DIRECT_MODEL_CONFIG))

    config = structure_bkaidev_model_config(settings.BKAIDEV_MODEL_CONFIG)
    return _build_bkaidev_catalog(await _fetch_gateway_models(credential, transport=transport), config)


async def _fetch_gateway_models(
    credential: UserCredential | None,
    *,
    transport: httpx2.AsyncBaseTransport | None,
) -> list[GatewayModel]:
    """Return the models the gateway offers this app, from the cache while it is fresh."""
    # 网关按「签发 token 的应用」决定开放哪些模型，和是哪个用户无关，所以按应用缓存、所有用户共用。
    # 命中时连换票都省了。
    key = (build_bkaidev_llm_base_url(), settings.APP_CODE)

    # 登录态在查缓存之前就检查：否则同一个请求会不会 401，取决于别人刚才有没有把缓存填上。
    if credential is None:
        raise ModelCredentialMissingError("Calling bkaidev needs the user's BlueKing login, and the request has none")

    cached = gateway_models_cache.get(key)
    if cached is not None:
        return cached

    access = await resolve_bkaidev_model_access(credential, transport=transport)
    client = BkAidevGatewayClient(base_url=access.base_url, access_token=access.access_token, transport=transport)
    models = await client.list_models()

    # 只缓存成功的结果：失败原样报给这一次的用户，下一个请求接着去问网关。
    gateway_models_cache.put(key, models)
    return models


def _build_direct_catalog(config: DirectModelConfig) -> ModelCatalog:
    """Describe the one fixed model of a direct deployment."""
    model_id = config.model_id
    option = ModelOption(id=model_id, name=config.name or model_id, context_window=config.context_window)
    return ModelCatalog(source=ModelSource.DIRECT, allow_user_switch=False, default_model_id=model_id, models=[option])


def _build_bkaidev_catalog(gateway_models: list[GatewayModel], config: BkAidevModelConfig) -> ModelCatalog:
    """Narrow the gateway's models to the ones offered for picking, in the order they are shown."""
    # agent 靠工具干活，剔除明确不支持工具的模型；没给能力位的保留。
    usable = [
        model for model in gateway_models if model.properties is None or model.properties.support_tools is not False
    ]

    # 没有可选列表时不过滤，按网关顺序。
    picked = _pick_available(usable, config.available_models) if config.available_models else usable

    # 配了列表却一项都没命中，多半是配置没跟上网关的模型变化。退回全部能调工具的模型，
    # 免得用户面对一个空的下拉框。
    if config.available_models and not picked:
        logger.warning(
            "Nothing in available_models %s is offered by the bkaidev gateway; offering every tool-calling model",
            config.available_models,
        )
        picked = usable

    # default_model_id 取本服务的默认模型，不取上游的 default 标记。
    # default_model_name 是注入 Runtime 的 MODEL_NAME，和网关卡片的 id 是同一个值。
    if config.default_model_name not in {model.id for model in picked}:
        logger.warning(
            "The default model %s is not among the models offered for picking; check it is still open to this app",
            config.default_model_name,
        )

    return ModelCatalog(
        source=ModelSource.BKAIDEV,
        allow_user_switch=True,
        default_model_id=config.default_model_name,
        models=[_make_option_from_gateway(model) for model in picked],
    )


def _pick_available(usable: list[GatewayModel], patterns: list[str]) -> list[GatewayModel]:
    """Keep the gateway's models matched by the patterns, in the patterns' order."""
    picked: dict[str, GatewayModel] = {}
    for pattern in patterns:
        matched = [model for model in usable if fnmatchcase(model.id, pattern)]

        # 配了但上游没给（未对本应用开通、已下线，或不能调工具）：跳过，记下来让运维改配置。
        if not matched:
            logger.warning(
                "%s in available_models matches no tool-calling model offered by the bkaidev gateway", pattern
            )
            continue

        # 一项模式命中多个模型时按网关顺序；已经被前面的项选中的留在原位，不重复出现。
        for model in matched:
            picked.setdefault(model.id, model)

    return list(picked.values())


def _make_option_from_gateway(model: GatewayModel) -> ModelOption:
    """Show a gateway model with what its card says, and nothing it does not."""
    # 网关卡片没有展示名，用 ID 代替。
    properties = model.properties
    return ModelOption(
        id=model.id,
        name=model.id,
        context_window=properties.max_model_len if properties else None,
        supports_vision=properties.support_vision if properties else False,
    )
