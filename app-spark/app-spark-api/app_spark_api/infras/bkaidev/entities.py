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

"""What this service reads out of the bkaidev LLM gateway's answers."""

from __future__ import annotations

import logging

import attrs
from cattrs import Converter
from cattrs.errors import BaseValidationError
from cattrs.gen import make_dict_structure_fn, override
from cattrs.v import transform_error

from app_spark_api.infras.bkaidev.exceptions import BkAidevGatewayError
from app_spark_api.utils.attrs import make_strict_structure_hook

logger = logging.getLogger(__name__)


@attrs.frozen
class GatewayModelProperty:
    """The gateway's own extension to an OpenAI model card, its property field.

    :param support_tools: Whether the model can call tools; None when the gateway does not say.
    :param support_vision: Whether the model accepts images.
    :param max_model_len: Context window in tokens, None when the gateway does not say.
    """

    support_tools: bool | None = None
    support_vision: bool = False
    max_model_len: int | None = None


@attrs.frozen
class GatewayModel:
    """One model the gateway lets this app call, as listed by GET /models.

    :param id: The llm_code, sent back as the model name of a chat completion.
    :param properties: The gateway's extension fields; None when the card has none.
    """

    id: str
    properties: GatewayModelProperty | None = None


# 上游卡片上的字段远多于这里读的那几个，而且会继续加，所以不开 forbid_extra_keys。
# 读到的字段则按 JSON 类型严格校验："support_tools": "false" 被宽松转换成 True 的话，
# 一个不能调工具的模型就混进了列表。
_converter = Converter()
_converter.register_structure_hook(str, make_strict_structure_hook(str))
_converter.register_structure_hook(bool, make_strict_structure_hook(bool))
_converter.register_structure_hook(int, make_strict_structure_hook(int, reject_bool=True))
# Python 属性避开 property 这个内置名，JSON 仍用网关的字段名。
_converter.register_structure_hook(
    GatewayModel,
    make_dict_structure_fn(GatewayModel, _converter, properties=override(rename="property")),
)


def structure_gateway_model_list(payload: object) -> list[GatewayModel]:
    """Read the models out of a GET /models body, skipping the cards that cannot be read.

    :param payload: Decoded JSON body.
    :return: The readable models, in the gateway's order.
    :raises BkAidevGatewayError: If the body is not a model list, or none of its cards can be read.
    """
    # 外层结构不对说明整张响应不可信。{"data": {}} 或 {"data": ""} 不能当成「没有模型」。
    cards = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(cards, list):
        raise BkAidevGatewayError("Unreadable GET /models response: $.data is not a list")

    # 卡片由网关维护且字段还在增加。一张与本服务无关的卡片写坏了，不该让所有人的下拉框都 502，
    # 所以逐张读，读不了的跳过。support_tools 类型不对的卡片也跳过，不会混进不能调工具的模型。
    models = []
    for index, card in enumerate(cards):
        path = f"$.data[{index}]"
        try:
            models.append(_converter.structure(card, GatewayModel))
        except BaseValidationError as exc:
            # 异常组自己的 str() 只有「N sub-exceptions」，展开才知道是哪个字段不对。
            logger.warning("Skipping an unreadable GET /models card: %s", "; ".join(transform_error(exc, path=path)))
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning("Skipping an unreadable GET /models card at %s: %s", path, exc)

    # 有卡片却一张都读不了，多半是网关改了格式，和真的没有模型是两回事。
    if cards and not models:
        raise BkAidevGatewayError(f"Unreadable GET /models response: none of its {len(cards)} cards can be read")

    return models
