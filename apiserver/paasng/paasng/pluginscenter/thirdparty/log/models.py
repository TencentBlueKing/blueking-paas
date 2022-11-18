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
from typing import Dict, Generic, List, Literal, Optional, TypeVar, Union

import arrow
from attrs import converters, define, field, fields
from elasticsearch_dsl.aggs import FieldBucketData
from elasticsearch_dsl.response import Hit
from rest_framework.fields import get_attribute

from paasng.pluginscenter.definitions import ElasticSearchParams


@define
class StandardOutputLogLine:
    """标准输出日志结构"""

    timestamp: int
    message: str


@define
class StructureLogLine:
    """结构化日志结构"""

    timestamp: int
    message: str
    raw: Dict


@define
class IngressLogLine:
    """ingress 访问日志结构"""

    timestamp: int
    message: str
    raw: Dict

    method: Optional[str] = field(init=False, converter=converters.optional(str))
    path: Optional[str] = field(init=False, converter=converters.optional(str))
    status_code: Optional[int] = field(init=False, converter=converters.optional(int))
    response_time: Optional[float] = field(init=False, converter=converters.optional(float))
    client_ip: Optional[str] = field(init=False, converter=converters.optional(str))
    bytes_sent: Optional[int] = field(init=False, converter=converters.optional(int))
    user_agent: Optional[str] = field(init=False, converter=converters.optional(str))
    http_version: Optional[str] = field(init=False, converter=converters.optional(str))

    def __attrs_post_init__(self):
        for attr in fields(type(self)):
            if not attr.init:
                setattr(self, attr.name, self.raw.get(attr.name))


MLine = TypeVar("MLine")


@define
class Logs(Generic[MLine]):
    logs: List[MLine]
    total: int
    dsl: str


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


def clean_logs(
    logs: List[Hit],
    search_params: ElasticSearchParams,
) -> List[Dict]:
    """从 ES 日志中提取插件开发中心关心的字段"""
    cleaned = []
    for log in logs:
        cleaned.append(
            {
                "timestamp": format_timestamp(
                    get_attribute(log, search_params.timeField.split(".")), search_params.timeFormat
                ),
                "message": get_attribute(log, search_params.messageField.split(".")),
                "raw": log.to_dict(),
            }
        )
    return cleaned


def clean_histogram_buckets(buckets: FieldBucketData) -> Dict:
    """从 ES 聚合桶中提取插件开发中心关心的字段"""
    series = []
    timestamps = []
    for bucket in buckets:
        timestamps.append(format_timestamp(bucket["key"], input_format="timestamp[ns]"))
        series.append(bucket["doc_count"])
    return {
        "timestamps": timestamps,
        "series": series,
    }


def format_timestamp(
    value: Union[str, int, float], input_format: Literal["timestamp[s]", "timestamp[ns]", "datetime"]
) -> int:
    """format a value to timestamp in seconds

    :params value: 输入的时间数据
    :params input_format: 输入的 value 格式
    """
    if input_format == "timestamp[s]":
        return int(value)
    elif input_format == "timestamp[ns]":
        return int(value) // 1000
    else:
        return int(arrow.get(value).timestamp)
