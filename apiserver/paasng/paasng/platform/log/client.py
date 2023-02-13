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
from collections import Counter, defaultdict
from dataclasses import dataclass
from operator import itemgetter
from typing import Any, Dict, List, Optional, Tuple, Type

import pytz
from django.conf import settings
from django.utils import timezone
from elasticsearch import Elasticsearch
from elasticsearch.helpers import ScanError
from elasticsearch_dsl import Index, Search
from elasticsearch_dsl.aggs import A
from elasticsearch_dsl.response import Response
from pydantic import parse_obj_as
from typing_extensions import Protocol

from paasng.utils.datetime import (
    calculate_gap_seconds_interval,
    calculate_interval,
    get_time_delta,
    strftime_ms,
    time_to_epoch_millis,
)
from paasng.utils.text import calculate_percentage

from .constants import LOG_FILTER_FIELD_MAPS
from .exceptions import LogQueryError
from .filters import BaseAppFilter
from .models import FieldFilter, LogCountTimeHistogram, LogPage, SimpleDomainSpecialLanguage, StandardOutputLogScroll
from .utils import detect_indexes, get_es_term, parse_simple_dsl_to_dsl

logger = logging.getLogger(__name__)


class ScrollableLogsResult(Protocol):
    """Callable for making scrollable logs, with some extra data"""

    def __call__(self, scroll_id: str, logs: Response, total: int) -> Any:
        ...


@dataclass
class LogClient:
    """
    Log client
    packed several methods, suck as query_log_list, get_field_filters
    """

    app_filter: BaseAppFilter
    # query conditions: a simple dsl object
    query_conditions: SimpleDomainSpecialLanguage

    index_pattern: str
    # dynamic or static time range
    smart_time_range: 'SmartTimeRange'

    # highlight tag
    pre_tag: str = settings.BK_LOG_HIGHLIGHT_TAG[0]
    post_tag: str = settings.BK_LOG_HIGHLIGHT_TAG[1]
    log_page_class: Type[LogPage] = LogPage

    def __post_init__(self):
        start_time, end_time = self.smart_time_range.get_head_and_tail(all_epoch_millis=True, raw_obj=True)
        indexes = detect_indexes(start_time, end_time, index_pattern=self.index_pattern)
        if not indexes:
            raise LogQueryError("detect indexes fail")

        self.indexes = indexes

        self.client = Elasticsearch(settings.ELASTICSEARCH_HOSTS)
        self.es_index = Index(self.indexes, using=self.client)

    def _get_properties_mapping(self) -> dict:
        """获取属性映射"""

        # 当前不支持同一批次 index (类似 aa-2021.04.20,aa-2021.04.19) 拥有不同的 mapping
        # 直接获取最新的 mapping
        # 如果同一批次 index mapping 发生变化，可能会导致日志查询为空
        mapping = list(self.es_index.get_mapping().values())[0]
        return mapping["mappings"]["properties"]

    def _make_base_query(self, order_by_time: Optional[str] = None, enable_highlight: bool = True) -> Search:
        """
        base query filter by:
        - app_info(powered by app_filter)
        - [start_time, end_time](powered by smart_time_range)
        - env
        - other terms
        order_by_time:
            None -> "don't order by time"
            asc -> "order by time asc"
            desc -> "order by time desc"
        """
        mappings = self._get_properties_mapping()
        dsl = parse_simple_dsl_to_dsl(self.query_conditions, mappings)
        q = (
            Search(using=self.client, index=self.indexes)
            .params(request_timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT)
            .filter("range", **self.smart_time_range.get_time_range_filter())
            .query(dsl)
        )
        q = self.app_filter.filter_by_app(q, mappings)

        # 将 dsl 添加进 query 参数, 并限制只高亮 dsl 查询条件中的字段
        if enable_highlight:
            highlight_dsl = parse_simple_dsl_to_dsl(
                self.query_conditions.copy().remove_regular_conditions(mappings), mappings
            )
            q = (
                q.highlight("json.*", number_of_fragments=0)
                # require_field_match 必须为 False, 否则只有指定 json.message: xxx 才会高亮 message 的内容
                .highlight_options(
                    pre_tags=[self.pre_tag], post_tags=[self.post_tag], require_field_match=False
                ).highlight_options(highlight_query=highlight_dsl.to_dict())
            )

        # LogList api 需要根据时间进行排序
        if order_by_time and order_by_time in ["desc", "asc"]:
            sort_params = dict()
            if self.query_conditions.sort:
                sort_params.update({k: {"order": v} for k, v in self.query_conditions.sort.items()})

            sort_params.update({"@timestamp": {"order": order_by_time}, "ns": {"order": order_by_time}})
            q = q.sort(sort_params)

        logger.info("log query: %s", q.to_dict())
        return q

    def make_scroll_query(
        self,
        order_by_time: str = "desc",
        scroll="5m",
        request_timeout: int = settings.DEFAULT_ES_SEARCH_TIMEOUT,
        size=200,
    ) -> Response:
        """创建一个 ES scroll(滚屏) 查询, Scroll 有效时间默认为 5min"""
        q = self._make_base_query(order_by_time=order_by_time)

        resp = self.client.search(
            body=q.to_dict(), scroll=scroll, size=size, request_timeout=request_timeout, index=self.indexes
        )
        return Response(q, resp)

    def fetch_logs_by_scroll_id(
        self, scroll_id, scroll="5m", request_timeout: int = settings.DEFAULT_ES_SEARCH_TIMEOUT
    ) -> Response:
        """使用已有的 scroll id 查询日志"""
        resp = Response(
            self._make_base_query(),
            self.client.scroll(scroll_id=scroll_id, params=dict(scroll=scroll, request_timeout=request_timeout)),
        )

        # check if we have any errrors
        if not resp.success():
            failed = resp._shards.failed
            total = resp._shards.total
            logger.warning(
                'Scroll request has failed on %d shards out of %d.',
                failed,
                total,
            )
            raise ScanError(
                scroll_id,
                'Scroll request has failed on %d shards out of %d.' % (failed, total),
            )
        return resp

    def _execute(self, q):
        resp = q.execute()
        if not resp.success():
            logger.error("execute fail! query=%s", q.to_dict())
            return False, None
        return True, resp

    def aggregate_log_count_histogram(self):
        """
        从 ES 统计 [日志数量 x 时间] 直方图
        es query result:
            {"histogram":
                {"buckets": [
                    {
                        "service_top":
                        {
                            "buckets": [
                                { "key": "redis", "doc_count": 217 },
                                { "key": "django", "doc_count": 23 }
                            ],
                            "sum_other_doc_count": 0,
                            "doc_count_error_upper_bound": 0
                        },
                        "key_as_string": "2018-09-06T15:00:00.000+08:00",
                        "key": 1536217200000,
                        "doc_count": 377
                    },
                    ]
                }
            }
        """
        q = self._make_base_query(enable_highlight=False)

        aggs_by_dh = A(
            "date_histogram",
            field="@timestamp",
            interval=self.smart_time_range.get_interval(),
            time_zone=settings.TIME_ZONE,
            min_doc_count=1,
        )
        q.aggs.bucket('histogram', aggs_by_dh)

        q = q[:0]
        logger.debug("_get_total_chart query=%s", q.to_dict())
        ok, resp = self._execute(q)
        if not ok:
            return {}

        return resp.aggregations.to_dict()

    def parse_log_count_histogram(self, data) -> LogCountTimeHistogram:
        """
        将从 ES 查询到的 [日志数量 x 时间] 直方图转换成 LogCountTimeHistogram
        """
        timeline = []
        buckets = data["histogram"]["buckets"]
        series = []
        for bucket in buckets:
            ts = bucket["key"]
            timeline.append(strftime_ms(ts))
            series.append(bucket["doc_count"])
        return parse_obj_as(LogCountTimeHistogram, {"series": series, "timeline": timeline})

    def get_log_count_histogram(self) -> LogCountTimeHistogram:
        """
        从 ES 查询到的 [日志数量 x 时间] 直方图
        """
        data = self.aggregate_log_count_histogram()
        return self.parse_log_count_histogram(data)

    def parse_buckets_as_filters(self, data) -> List[FieldFilter]:
        """
        将从 ES 查询到的 `field buckets` 转换成 `FieldFilter`
        :param data: ES 使用 bucket 聚合统计返回的结构体
        """
        legacy_fields = LOG_FILTER_FIELD_MAPS
        filters = []

        for title in data.keys():
            if title in legacy_fields:
                field = legacy_fields[title]
            else:
                logger.error("`%s` is an invalid field", title)
                continue

            buckets = data[title]["buckets"]

            key_counts = []
            total = 0
            for bucket in buckets:
                key = bucket["key"]
                count = bucket["doc_count"]

                key_counts.append((key, count))
                total += count

            options = []
            for key, count in key_counts:
                percentage = calculate_percentage(count, total)
                options.append((key, percentage))

            if total == 0:
                # 该 field 无值可选, 直接忽略掉
                continue

            filters.append(
                {
                    "name": title,
                    "chinese_name": field.chinese_name,
                    "key": field.query_term,
                    "options": options,
                    "total": total,
                }
            )
        # 根据 field 在所有日志记录中出现的次数进行降序排序
        filters.sort(key=itemgetter("total"), reverse=True)
        return parse_obj_as(List[FieldFilter], filters)

    def parse_logs_as_filters(self, data: Response) -> List[FieldFilter]:
        """
        从 ES 日志中的 json.* 字段统计出 filters
        """
        filtered_fields = self.log_page_class.filter_fields(self.client, self.es_index)

        # 在内存中统计 filters 的可选值
        field_counter: Dict[str, Counter] = defaultdict(Counter)
        for log_line in self.log_page_class.cast_logs(data):
            for field, value in log_line.detail.items():
                if field not in filtered_fields or not filtered_fields[field].is_filter:
                    continue
                try:
                    field_counter[field][value] += 1
                except TypeError:
                    logger.warning("Field<%s> got an unhashable value: %s", field, value)

        filters = []
        for title, values in field_counter.items():
            field = filtered_fields[title]
            options = []
            total = sum(values.values())

            if total == 0:
                # 该 field 无值可选, 直接忽略掉
                continue

            for value, count in values.items():
                percentage = calculate_percentage(count, total)
                options.append((value, percentage))

            filters.append(
                {
                    "name": title,
                    "chinese_name": field.chinese_name,
                    "key": field.query_term,
                    "options": options,
                    "total": total,
                }
            )
        # 根据 field 在所有日志记录中出现的次数进行降序排序
        filters.sort(key=itemgetter("total"), reverse=True)
        return parse_obj_as(List[FieldFilter], filters)

    def get_field_filters(self, include_es_fields: bool = False, count_num: int = 200) -> List[FieldFilter]:
        """
        es query result:
            [
              {"name": "Env", "key": "meta.env.keyword",
               "options": [["development", "100.00%"]]},
              {"name": "Type", "key": "trace_type.keyword",
               "options": [["redis", "48.52%"], ["sql", "44.26%"], ["http", "7.22%"]]},
            ]
        """
        q = self._make_base_query(enable_highlight=False)
        mapping = self._get_properties_mapping()
        for field in LOG_FILTER_FIELD_MAPS.values():
            q.aggs.bucket(
                field.title,
                'terms',
                field=get_es_term(field.query_term, mapping),
                size=5,
                order=dict(_count="desc"),
            )

        if include_es_fields:
            # 拉取最近 200 条日志, 用于统计 json.* 的可能值
            q = q[0:count_num]
        else:
            # 不统计 json.* 的可选值, 则设置拉取 0 条日志, 仅进行聚合统计
            q = q[:0]

        logger.debug("get_field_filters query=%s", q.to_dict())
        ok, resp = self._execute(q)
        if not ok:
            return []

        fields_bucket = resp.aggregations.to_dict()
        default_filters = self.parse_buckets_as_filters(fields_bucket)
        if include_es_fields:
            fields_filters = self.parse_logs_as_filters(resp)
            return default_filters + fields_filters
        return default_filters

    def query_logs(self, page, page_size, page_class: Optional[Type[LogPage]] = None) -> Optional[LogPage]:
        """
        :param page: 当前页
        :param page_size: 页大小
        :param page_class: LogPage 类
        """
        if not page_class:
            page_class = self.log_page_class

        q = self._make_base_query(order_by_time="desc")

        start = (page - 1) * page_size
        end = page * page_size
        q = q[start:end]

        logger.debug("query_trace_list query=%s", q.to_dict())
        ok, resp = self._execute(q)
        if not ok:
            return None

        total = q.count()
        return page_class(page=dict(page=page, page_size=page_size, total=total), logs=resp)

    def query_scrollable_logs(
        self, scroll_id: Optional[str] = None, result_type: Optional[ScrollableLogsResult] = None
    ):
        """Query scrollable logs, used by stdout/stderr logs and bk_plugin logs

        :param scroll_id: The identifier for scroll logs
        :param result_type: callback type for making results, using `StandardOutputLogScroll` by default
        """
        if scroll_id is None:
            logs = self.make_scroll_query(order_by_time="desc")
        else:
            logs = self.fetch_logs_by_scroll_id(scroll_id=scroll_id)

        try:
            new_scroll_id = logs._scroll_id
        except AttributeError as e:
            raise ScanError(scroll_id, "Can't not get next scroll_id from ES.") from e

        r_type = result_type or StandardOutputLogScroll
        return r_type(scroll_id=new_scroll_id, logs=logs, total=logs._search.count())


class SmartTimeRange:
    def __init__(self, time_range: str, start_time: Optional[str] = None, end_time: Optional[str] = None):
        """A tool class for LogClient, transfer time_range[start_time, end_time] to ES format

        :param time_range: Dynamic or static time range. dynamic examples: 1s, 5m, 10h, static: customized
        :param start_time: Optional, necessary if time_range is `customized`
        :param end_time: Optional, necessary if time_range is `customized`
        """
        self.time_range = time_range

        if self.time_range == "customized":
            if start_time is None or end_time is None:
                raise ValueError("start time & end time is necessary if time range is customized")

            self.start_time_obj = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            self.end_time_obj = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        else:
            self.end_time_obj = datetime.datetime.now()
            self.start_time_obj = self.end_time_obj - get_time_delta(self.time_range)

            start_time = datetime.datetime.strftime(self.start_time_obj, "%Y-%m-%d %H:%M:%S")
            end_time = datetime.datetime.strftime(self.end_time_obj, "%Y-%m-%d %H:%M:%S")

        self.start_time = start_time
        self.end_time = end_time

    @property
    def is_absolute(self):
        return self.time_range == "customized"

    @staticmethod
    def _get_epoch_millis(datetime_string: str, is_end=False):
        time_dt = datetime.datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")
        current_tz = timezone.get_current_timezone()
        time_dt_local = current_tz.localize(time_dt)
        time_ts = time_dt_local.astimezone(pytz.utc)

        # time to epoch millis
        return time_to_epoch_millis(time_ts, is_end)

    def get_head_and_tail(self, all_epoch_millis=False, raw_obj: bool = False) -> Tuple:
        if raw_obj:
            return self.start_time_obj, self.end_time_obj

        if self.is_absolute or all_epoch_millis:
            return self._get_epoch_millis(self.start_time), self._get_epoch_millis(self.end_time, is_end=True)
        else:
            return f"now-{self.time_range}", "now"

    def get_interval(self):
        if self.is_absolute:
            # currently, use narrow interval,
            # if the design of apm UI make each graph width > 40% then use wide interval
            start_time, end_time = self.get_head_and_tail()
            return calculate_interval(start_time, end_time)
        else:
            # NOTE: replace `seconds` with `total_seconds`
            return calculate_gap_seconds_interval(get_time_delta(self.time_range).total_seconds())

    def get_time_range_filter(self):
        start_time, end_time = self.get_head_and_tail()
        time_range_filter = {"@timestamp": {"gte": start_time, "lte": end_time}}
        if self.is_absolute:
            time_range_filter["@timestamp"]["format"] = "epoch_millis"

        return time_range_filter
