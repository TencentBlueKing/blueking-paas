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
from typing import TYPE_CHECKING

import attrs
from django.conf import settings

from app_spark_api.agent.runtime.constants import ModelSource
from app_spark_api.agent.runtime.entities import structure_bkaidev_model_config, structure_direct_model_config
from app_spark_api.agent.runtime.model_access import get_model_source, resolve_bkaidev_model_access
from app_spark_api.infras.bkaidev import BkAidevGatewayClient

if TYPE_CHECKING:
    import httpx2

    from app_spark_api.agent.runtime.entities import BkAidevModelConfig, DirectModelConfig
    from app_spark_api.infras.bk_access_token import UserCredential
    from app_spark_api.infras.bkaidev import GatewayModel

logger = logging.getLogger(__name__)


@attrs.frozen
class ModelOption:
    """一个可选模型。

    :param code: 模型编码。
    :param name: 展示名称。
    :param context_window: 上下文窗口。
    :param supports_vision: 是否支持图像输入。
    """

    code: str
    name: str
    context_window: int | None = None
    supports_vision: bool = False


@attrs.frozen
class ModelCatalog:
    """当前部署可选的模型。

    :param source: 模型来源。
    :param switchable: 是否可切换模型。
    :param default_code: 默认模型编码。
    :param models: 可选模型。
    """

    source: ModelSource
    switchable: bool
    default_code: str
    models: list[ModelOption]


async def list_models(
    credential: UserCredential | None,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> ModelCatalog:
    """Return the models this user may pick from, and the one a turn that picks none runs on.

    Asks the gateway every time and keeps nothing: the list is fetched once per opened
    conversation page, and the token it is fetched with belongs to this user alone.

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
    access = await resolve_bkaidev_model_access(credential, transport=transport)
    client = BkAidevGatewayClient(base_url=access.base_url, access_token=access.access_token, transport=transport)
    return _build_bkaidev_catalog(await client.list_models(), config)


def _build_direct_catalog(config: DirectModelConfig) -> ModelCatalog:
    """Describe the one fixed model of a direct deployment."""
    # model 形如 deepseek:deepseek-v4-flash。冒号后的部分才是用户认得的模型名，也是一轮对话提交的值。
    code = config.model.partition(":")[2] or config.model
    option = ModelOption(code=code, name=config.name or code, context_window=config.context_window)
    return ModelCatalog(source=ModelSource.DIRECT, switchable=False, default_code=code, models=[option])


def _build_bkaidev_catalog(gateway_models: list[GatewayModel], config: BkAidevModelConfig) -> ModelCatalog:
    """Narrow the gateway's models to the ones offered for picking, in the order they are shown."""
    # agent 靠工具干活，剔除明确不支持工具的模型；没给能力位的保留。
    usable = [
        model for model in gateway_models if model.properties is None or model.properties.support_tools is not False
    ]

    # 有推荐列表时取交集，按推荐顺序排。
    if config.recommended_models:
        picked = _pick_recommended(usable, config.recommended_models)

    # 没有推荐列表时不过滤，按网关顺序。
    else:
        picked = usable

    # default_code 取本服务的默认模型，不取上游的 default 标记。
    if config.default_model_name not in {model.code for model in picked}:
        logger.warning(
            "The default model %s is not among the models offered for picking; check it is still open to this app",
            config.default_model_name,
        )

    return ModelCatalog(
        source=ModelSource.BKAIDEV,
        switchable=True,
        default_code=config.default_model_name,
        models=[_make_option_from_gateway(model) for model in picked],
    )


def _pick_recommended(usable: list[GatewayModel], recommended: list[str]) -> list[GatewayModel]:
    """Keep the recommended models the gateway offers, in the recommended order."""
    by_code = {model.code: model for model in usable}
    picked = []
    for code in recommended:
        model = by_code.get(code)

        # 推荐了但上游没给（未对本应用开通、已下线，或不能调工具）：不返回，记下来让运维改配置。
        if model is None:
            logger.warning(
                "Recommended model %s is not offered by the bkaidev gateway as a tool-calling model; leaving it out",
                code,
            )
            continue

        picked.append(model)

    return picked


def _make_option_from_gateway(model: GatewayModel) -> ModelOption:
    """Show a gateway model with what its card says, and nothing it does not."""
    # 网关卡片没有展示名，用编码代替。
    properties = model.properties
    return ModelOption(
        code=model.code,
        name=model.code,
        context_window=properties.max_model_len if properties else None,
        supports_vision=properties.support_vision if properties else False,
    )
