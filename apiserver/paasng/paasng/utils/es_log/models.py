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
from typing import Any, Dict, Generic, List, Optional, Tuple, TypedDict, TypeVar

from attr import define, field


class FlattenLog(TypedDict):
    """
    :param timestamp: linux timestamp(seconds)
    :param message: log message field
    :param raw: flatten es log, can get field by es format, e.g. "json.message"
    """

    timestamp: int
    message: str
    raw: Dict[str, Any]


MLine = TypeVar("MLine")


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
    :param key: query_term: get 参数中的 key
    :param options: 该 field 的可选项
    :param total: 该 field 出现的总次数
    """

    name: str
    key: str
    options: List[Tuple[str, str]] = field(factory=list)
    total: int = 0
