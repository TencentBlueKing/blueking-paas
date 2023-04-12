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
import datetime
import logging
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

import arrow
from _operator import attrgetter
from elasticsearch_dsl.response.aggs import FieldBucketData
from rest_framework.fields import get_attribute

from paasng.utils.es_log.models import FieldFilter
from paasng.utils.text import calculate_percentage

if TYPE_CHECKING:
    from paasng.utils.es_log.time_range import SmartTimeRange

logger = logging.getLogger(__name__)


def flatten_structure(structured_fields: Dict, parent: Optional[str] = None) -> Dict[str, Any]:
    """接收一个包含层级关系的结构体，并将其扁平化，返回转换后的结构体

    :param structured_fields: 包含层级关系的结构体
    :param parent: 父级字段的名称, 为空时即无父级字段

    :return: 转换后的扁平化结构体
    """
    ret: Dict[str, Any] = dict()
    for sub_key, value in structured_fields.items():
        if parent is None:
            key = sub_key
        else:
            key = f"{parent}.{sub_key}"
        if isinstance(value, dict):
            sub = flatten_structure(value, key)
            ret.update(sub)
            continue
        ret[key] = value
    return ret


def clean_histogram_buckets(buckets: FieldBucketData) -> Dict:
    """从 ES 聚合桶中提取 PaaS 关心的字段"""
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


def count_filters_options(logs: List, properties: Dict[str, FieldFilter]) -> List[FieldFilter]:
    """统计 ES 日志的可选字段, 并填充到 filters 的 options"""
    # 在内存中统计 filters 的可选值
    field_counter: Dict[str, Counter] = defaultdict(Counter)
    log_fields = [(f, f.split(".")) for f in properties.keys()]
    for log in logs:
        for log_field, split_log_field in log_fields:
            try:
                value = get_attribute(log, split_log_field)
            except (AttributeError, KeyError):
                continue
            try:
                field_counter[log_field][value] += 1
            except TypeError:
                logger.warning("Field<%s> got an unhashable value: %s", log_field, value)

    result = []
    for title, values in field_counter.items():
        options = []
        total = sum(values.values())
        if total == 0:
            # 该 field 无值可选时, 不允许使用该字段作为过滤条件
            continue

        for value, count in values.items():
            percentage = calculate_percentage(count, total)
            options.append((value, percentage))
        result.append(FieldFilter(name=title, key=properties[title].key, options=options, total=total))
    # 根据 field 在所有日志记录中出现的次数进行降序排序, 再根据 key 的字母序排序(保证前缀接近的 key 靠近在一起, 例如 json.*)
    return sorted(result, key=attrgetter("total", "key"), reverse=True)


def filter_indexes_by_time_range(indexes: List[str], time_range: "SmartTimeRange") -> List[str]:
    """Attempt to filter indexes within the time_range from indexes, Only indexes ending with YYYY.MM.DD are supported

    :param indexes: List of indexes
    :param time_range: time_range given
    """
    pattern = re.compile(r"^.*?-(?P<date>\d\d\d\d\.\d\d.\d\d)$")
    failure_match_indexes = []
    picked_indexes = []
    start_date = time_range.start_time.date()
    end_date = time_range.end_time.date()
    for index in indexes:
        match_result = pattern.match(index)
        if not match_result:
            failure_match_indexes.append(index)
            continue

        date_str = match_result.groupdict()["date"]
        try:
            index_date = datetime.datetime.strptime(date_str, "%Y.%m.%d").date()
        except ValueError:
            failure_match_indexes.append(index)
            continue

        if start_date <= index_date <= end_date:
            picked_indexes.append(index)
    if failure_match_indexes:
        logger.debug("some indexes is invalid, %s", failure_match_indexes)
    return picked_indexes
