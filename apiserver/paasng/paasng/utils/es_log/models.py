# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypedDict, TypeVar, Union

from attrs import define, field, fields

from paasng.platform.log.exceptions import LogLineInfoBrokenError

NOT_SET = object()
_ConverterType = Callable[[Any], Any]
_GetterType = Callable[[Dict[str, Any]], Any]

_FlagField = "extra_log_field"
_GetterField = "getter"


def init_field_form_raw(self):
    """extract extra log field from raw, All fields except for FlattenLog are extra fields.

    default getter will try to set attr to raw[attr.name]
    If the attr.name is not the field name in raw, you can set getter in metadata the override the getter

    e.g.

    plugin_code: str = field(init=False, metadata={"getter": get_field_form_raw("app_code")})
    """
    for attr in fields(type(self)):
        if attr.metadata.get(_FlagField):
            getter = attr.metadata.get(_GetterField) or field_extractor_factory(attr.name)
            setattr(self, attr.name, getter(self.raw))
    for k, v in self.raw.items():
        if v is NOT_SET:
            self.raw[k] = None


class FlattenLog(TypedDict):
    """
    :param timestamp: linux timestamp(seconds)
    :param message: log message field
    :param raw: flatten es log, can get field by es format, e.g. "json.message"
    """

    timestamp: int
    message: str
    raw: Dict[str, Any]


@define
class LogLine:
    """LogLine is object type of FlattenLog

    :param timestamp: linux timestamp(seconds)
    :param message: log message field
    :param raw: flatten es log, can get field by es format, e.g. "json.message"
    """

    timestamp: int
    message: str
    raw: Dict[str, Any]

    __attrs_post_init__ = init_field_form_raw


def extra_field(source: Optional[Union[str, _GetterType]] = None, converter: Optional[_ConverterType] = None) -> Any:
    """extra_field is used to declare extra for subclass of FlattenLog,
    by default, the value of `extra_field` will be extract by field_extractor_factory(field_name)(raw)
    but if source is provided, `the value will be extract by field_extractor_factory(source)(raw) or source(raw)

    :param source: override source
    :param converter: attrs converter
    """
    metadata: Dict[str, Any] = {_FlagField: True}
    if source:
        if isinstance(source, str):
            metadata[_GetterField] = field_extractor_factory(source)
        else:
            metadata[_GetterField] = source
    return field(init=False, metadata=metadata, converter=converter)


def field_extractor_factory(field_key: str) -> _GetterType:
    """返回一个函数，用于从原始日志字典中提取指定字段的值

    :param field_key: 要提取值的字段名称(ES语法, 例如 json.message)
    """

    def core(raw_log: Dict[str, Any]) -> Any:
        if field_key not in raw_log or raw_log[field_key] is NOT_SET:
            raise LogLineInfoBrokenError(field_key)
        return raw_log[field_key]

    return core


MLine = TypeVar("MLine", bound=LogLine)


@define
class Logs(Generic[MLine]):
    logs: List[MLine]
    total: int
    dsl: str
    scroll_id: Optional[str] = None


@define
class DataBucket:
    count: str


@define
class DateHistogram:
    # 按时间排序的值
    series: List[int]
    # Series 中对应位置记录的时间点
    timestamps: List[int]
    dsl: str


@define
class FieldFilter:
    """字段选择器
    :param name: 查询字段的 title
    :param key: query_term: get 参数中的 key, 对于 text 类型的字段, key 是 `name` + `.keyword`
    :param options: 该 field 的可选项
    :param total: 该 field 出现的总次数
    """

    name: str
    key: str
    options: List[Tuple[str, str]] = field(factory=list)
    total: int = 0
