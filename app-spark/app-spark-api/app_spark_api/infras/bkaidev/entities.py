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

from typing import TYPE_CHECKING

import attrs
from cattrs import Converter
from cattrs.errors import BaseValidationError
from cattrs.gen import make_dict_structure_fn, override
from cattrs.v import transform_error

from app_spark_api.infras.bkaidev.exceptions import BkAidevGatewayError

if TYPE_CHECKING:
    from collections.abc import Callable


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

    :param code: The llm_code, sent back as the model name of a chat completion.
    :param properties: The gateway's extension fields; None when the card has none.
    """

    code: str
    properties: GatewayModelProperty | None = None


@attrs.frozen
class GatewayModelList:
    """The body of GET /models: an OpenAI list object."""

    data: list[GatewayModel]


def _structure_strict(expected: type, *, reject_bool: bool = False) -> Callable[[object, type], object]:
    """Build a hook that refuses a value of the wrong JSON type instead of coercing it."""

    def structure(value: object, _: type) -> object:
        # bool 是 int 的子类，不单独挡的话 "max_model_len": true 会被读成 1。
        if not isinstance(value, expected) or (reject_bool and isinstance(value, bool)):
            raise TypeError(f"Expected {expected.__name__}, got {type(value).__name__}")

        return value

    return structure


# 上游卡片上的字段远多于这里读的那几个，而且会继续加，所以不开 forbid_extra_keys。
# 读到的字段则按 JSON 类型严格校验："support_tools": "false" 被宽松转换成 True 的话，
# 一个不能调工具的模型就混进了列表。
_converter = Converter()
_converter.register_structure_hook(str, _structure_strict(str))
_converter.register_structure_hook(bool, _structure_strict(bool))
_converter.register_structure_hook(int, _structure_strict(int, reject_bool=True))
# Python 属性避开 id / property 这两个内置名，JSON 仍用网关的字段名。
_converter.register_structure_hook(
    GatewayModel,
    make_dict_structure_fn(
        GatewayModel,
        _converter,
        code=override(rename="id"),
        properties=override(rename="property"),
    ),
)


def structure_gateway_model_list(payload: object) -> list[GatewayModel]:
    """Read the models out of a GET /models body.

    :param payload: Decoded JSON body.
    :return: The models, in the gateway's order.
    :raises BkAidevGatewayError: If the body is not the shape GET /models promises.
    """
    try:
        return _converter.structure(payload, GatewayModelList).data
    except BaseValidationError as exc:
        # 异常组自己的 str() 只有「N sub-exceptions」，展开才知道是哪张卡片的哪个字段不对。
        reasons = "; ".join(transform_error(exc, path="$"))
        raise BkAidevGatewayError(f"Unreadable GET /models response: {reasons}") from exc
    except (AttributeError, TypeError, ValueError) as exc:
        raise BkAidevGatewayError(f"Unreadable GET /models response: {exc}") from exc
