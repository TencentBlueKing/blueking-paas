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
from functools import reduce
from operator import add, attrgetter
from typing import Dict, List, Optional, Protocol, Tuple, Union

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from elasticsearch import Elasticsearch
from elasticsearch.helpers import ScanError
from elasticsearch_dsl.aggs import DateHistogram
from elasticsearch_dsl.response import AggResponse, Response
from elasticsearch_dsl.response.aggs import FieldBucketData

from paasng.platform.log.constants import DEFAULT_LOG_BATCH_SIZE
from paasng.platform.log.exceptions import LogQueryError, NoIndexError
from paasng.platform.log.filters import (
    FieldFilter,
    agg_builtin_filters,
    count_filters_options_from_agg,
    count_filters_options_from_logs,
)
from paasng.platform.log.models import BKLogConfig, ElasticSearchConfig, ElasticSearchHost

# TODO: 避免引用插件开发中心的代码, 提取通用组件
from paasng.pluginscenter.definitions import PluginBackendAPIResource
from paasng.pluginscenter.thirdparty.utils import make_client
from paasng.utils.es_log.misc import filter_indexes_by_time_range
from paasng.utils.es_log.search import SmartSearch, SmartTimeRange


class LogClientProtocol(Protocol):
    """LogClient protocol, all log search backend should abide this protocol"""

    def execute_search(self, index: str, search: SmartSearch, timeout: int) -> Tuple[Response, int]:
        """Search log from index with search"""

    def execute_scroll_search(
        self, index: str, search: SmartSearch, timeout: int, scroll_id: Optional[str] = None, scroll="5m"
    ) -> Tuple[Response, int]:
        """search log(scrolling) from index with search"""

    def aggregate_date_histogram(self, index: str, search: SmartSearch, timeout: int) -> FieldBucketData:
        """Aggregate time-based histogram"""

    def aggregate_fields_filters(
        self, index: str, search: SmartSearch, mappings: dict, timeout: int
    ) -> List[FieldFilter]:
        """Aggregate fields filters"""

    def get_mappings(self, index: str, time_range: SmartTimeRange, timeout: int) -> dict:
        """query the mappings in es

        :raises LogQueryError: when no mappings found
        """


class BKLogClient:
    """BKLogClient is an implement of LogClientProtocol, the log search backend is bk log search"""

    def __init__(self, config: BKLogConfig, bk_username: str):
        self.config = config
        # TODO: 实现 BKLogClient
        self.client = make_client(
            PluginBackendAPIResource(apiName="log-search", path="esquery_dsl/", method="POST"), bk_username=bk_username
        )

    def execute_search(self, index: str, search: SmartSearch, timeout: int) -> Tuple[Response, int]:
        """search log from index with body and params, implement with bk-log"""
        data = {
            "indices": index,
            "scenario_id": self.config.scenarioID,
            "body": search.to_dict(),
        }
        resp = self._call_api(data, timeout)
        return Response(search.search, resp["data"]), resp["data"]["hits"]["total"]

    def execute_scroll_search(
        self, index: str, search: SmartSearch, timeout: int, scroll_id: Optional[str] = None, scroll="5m"
    ) -> Tuple[Response, int]:
        """search log(scrolling) from index with search"""
        raise NotImplementedError("TODO: 确认日志平台接口 /esquery_scroll/ 是否可用")

    def aggregate_date_histogram(self, index: str, search: SmartSearch, timeout: int) -> FieldBucketData:
        """Aggregate time-based histogram"""
        agg = DateHistogram(
            field=search.time_field,
            interval=search.time_range.detect_date_histogram_interval(),
            time_zone=settings.TIME_ZONE,
            min_doc_count=1,
        )
        search.search.aggs.bucket('histogram', agg)
        search.limit_offset(0, 0)
        data = {
            "indices": index,
            "scenario_id": self.config.scenarioID,
            "body": search.to_dict(),
        }
        resp = self._call_api(data, timeout)
        return AggResponse(search.search.aggs, search.search, resp["data"]["aggregations"]).histogram

    def aggregate_fields_filters(
        self, index: str, search: SmartSearch, mappings: dict, timeout: int
    ) -> List[FieldFilter]:
        """aggregate fields filter"""
        # 拉取最近 DEFAULT_LOG_BATCH_SIZE 条日志, 用于统计字段分布
        search = search.limit_offset(limit=DEFAULT_LOG_BATCH_SIZE, offset=0)
        data = {
            "indices": index,
            "scenario_id": self.config.scenarioID,
            "body": search.to_dict(),
        }
        resp = self._call_api(data, timeout)
        filters = {field: FieldFilter(name=field, key=field) for field in resp["data"]["select_fields_order"]}
        # 根据 field 在所有日志记录中出现的次数进行降序排序, 再根据 key 的字母序排序(保证前缀接近的 key 靠近在一起, 例如 json.*)
        filters = count_filters_options_from_logs(list(Response(search.search, resp["data"])), filters)
        return sorted(filters.values(), key=attrgetter("total", "key"), reverse=True)

    def get_mappings(self, index: str, time_range: SmartTimeRange, timeout: int) -> dict:
        """query the mappings in es"""
        raise NotImplementedError("TODO: 确认日志平台接口 /esquery_mapping/ 是否可用")

    def _get_indexes(self, index: str, time_range: SmartSearch) -> List[str]:
        """Get indexes within the time_range range from ES"""
        raise NotImplementedError

    def _call_api(self, data, timeout: int):
        if self.config.bkdataAuthenticationMethod:
            data["bkdata_authentication_method"] = self.config.bkdataAuthenticationMethod
        if self.config.bkdataDataToken:
            data["bkdata_data_token"] = self.config.bkdataDataToken
        return self.client.call(data=data, timeout=timeout)


class ESLogClient:
    """ESLogClient is an implement of LogClientProtocol, the log search backend is official elasticsearch"""

    def __init__(self, host: ElasticSearchHost):
        self.host = host
        self._client = Elasticsearch(hosts=[host.dict(exclude_none=True)])

    def execute_search(self, index: str, search: SmartSearch, timeout: int) -> Tuple[Response, int]:
        """search log from index with body and params, implement with es client"""
        es_index = self._get_indexes(index, search.time_range, timeout)
        response = Response(
            search.search,
            self._client.search(body=search.to_dict(), index=es_index, params={"request_timeout": timeout}),
        )
        return (response, self._get_response_count(es_index, search, timeout, response))

    def execute_scroll_search(
        self, index: str, search: SmartSearch, timeout: int, scroll_id: Optional[str] = None, scroll="5m"
    ) -> Tuple[Response, int]:
        """search log(scrolling) from index with search"""
        if scroll_id:
            response = Response(
                search.search,
                self._client.scroll(scroll_id=scroll_id, params={"scroll": scroll, "request_timeout": timeout}),
            )
        else:
            es_index = self._get_indexes(index, search.time_range, timeout)
            response = Response(
                search.search,
                self._client.search(
                    body=search.to_dict(), scroll=scroll, index=es_index, params={"request_timeout": timeout}
                ),
            )
        if not response.success():
            failed = response._shards.failed
            total = response._shards.total
            raise ScanError(
                scroll_id,
                'Scroll request has failed on %d shards out of %d.' % (failed, total),
            )
        return (response, self._get_response_count(index, search, timeout, response))

    def aggregate_date_histogram(self, index: str, search: SmartSearch, timeout: int) -> FieldBucketData:
        """Aggregate time-based histogram"""
        agg = DateHistogram(
            field=search.time_field,
            interval=search.time_range.detect_date_histogram_interval(),
            time_zone=settings.TIME_ZONE,
            min_doc_count=1,
        )
        search = search.agg("histogram", agg)
        search.limit_offset(0, 0)
        es_index = self._get_indexes(index, search.time_range, timeout)
        return AggResponse(
            search.search.aggs,
            search.search,
            self._client.search(body=search.to_dict(), index=es_index, params={"request_timeout": timeout})[
                "aggregations"
            ],
        ).histogram

    def aggregate_fields_filters(
        self, index: str, search: SmartSearch, mappings: dict, timeout: int
    ) -> List[FieldFilter]:
        """aggregate fields filter"""
        # 拉取最近 DEFAULT_LOG_BATCH_SIZE 条日志, 用于统计字段分布
        es_index = self._get_indexes(index, search.time_range, timeout)
        # 添加内置过滤条件查询语句, 内置过滤条件有 environment, process_id, stream
        search = agg_builtin_filters(search, mappings)
        search = search.limit_offset(limit=DEFAULT_LOG_BATCH_SIZE, offset=0)
        response = Response(
            search.search,
            self._client.search(body=search.to_dict(), index=es_index, params={"request_timeout": timeout}),
        )
        all_properties_filters = self._get_properties_filters(mappings)
        filters = count_filters_options_from_agg(response.aggregations.to_dict(), all_properties_filters)
        filters = count_filters_options_from_logs(list(response), filters)
        # 根据 field 在所有日志记录中出现的次数进行降序排序, 再根据 key 的字母序排序(保证前缀接近的 key 靠近在一起, 例如 json.*)
        return sorted(filters.values(), key=attrgetter("total", "key"), reverse=True)

    def get_mappings(self, index: str, time_range: SmartTimeRange, timeout: int) -> dict:
        """query the mappings in es"""
        # 当前假设同一批次的 index(类似 aa-2021.04.20,aa-2021.04.19) 拥有相同的 mapping, 因此直接获取最新的 mapping
        # 如果同一批次 index mapping 发生变化，可能会导致日志查询为空
        es_index = self._get_indexes(index, time_range, timeout)
        all_mappings = self._client.indices.get_mapping(es_index, params={"request_timeout": timeout})
        # 由于手动创建会没有 properties, 需要将无 properties 的 mappings 过滤掉
        all_not_empty_mappings = {
            key: mapping for key, mapping in all_mappings.items() if mapping["mappings"].get("properties")
        }
        if not all_not_empty_mappings:
            raise LogQueryError(_("No mappings available, maybe index does not exist or no logs at all"))
        first_mapping = all_not_empty_mappings[sorted(all_not_empty_mappings, reverse=True)[0]]
        docs_mappings: Dict = first_mapping["mappings"]["properties"]
        return docs_mappings

    def _get_indexes(self, index: str, time_range: SmartTimeRange, timeout: int) -> List[str]:
        """Get indexes within the time_range range from ES"""
        # 为了避免 ES 会提前创建 index 导致无法查询到 mappings, 需要精准控制使用的 indexes
        # 为了避免 ES indexes 未即时清理, 导致查询的 indexes 范围过大, 需要精准控制使用的 indexes
        # Note: 使用 stats 接口优化查询性能
        all_indexes = list(
            self._client.indices.stats(
                index, metric="fielddata", params={"request_timeout": timeout, "level": "indices"}
            )["indices"].keys()
        )
        if filtered_indexes := filter_indexes_by_time_range(all_indexes, time_range=time_range):
            return filtered_indexes
        # 当无法匹配到 indexes 时, 实际上也会查询不到日志, 所以无需报错, 只需要返回一部分 index 提供给 ES 查询即可
        if not all_indexes:
            raise NoIndexError
        return sorted(all_indexes)[-10:]

    def _get_response_count(
        self, index: Union[str, List[str]], search: SmartSearch, timeout: int, response: Response
    ) -> int:
        """get total field from es response if it had, or send a count response to es"""
        if response.hits.total.relation == "eq":
            return response.hits.total.value
        return self._client.count(body=search.to_dict(count=True), index=index, params={"request_timeout": timeout})[
            "count"
        ]

    def _get_properties_filters(self, mappings: dict) -> Dict[str, FieldFilter]:
        """获取属性映射"""
        # mappings 来自 get_mappings 函数
        # 为了简化 _clean_property 的递归代码, 传递给 _clean_property 时需要加上 {"properties": mappings} 这层封装
        return {f.name: f for f in self._clean_property([], {"properties": mappings})}

    @classmethod
    def _clean_property(cls, nested_name: List[str], mapping: Dict) -> List[FieldFilter]:
        """transform ES mapping to List[FieldFilter], will handle nested property by recursion

        Example Mapping:
        {
            "properties": {
                "age": {
                    "type": "integer"
                },
                "email": {
                    "type": "keyword"
                },
                "name": {
                    "type": "text"
                },
                "nested": {
                    "properties": {...}
                }
            }
        }
        """
        if "type" in mapping:
            field_name = ".".join(nested_name)
            return [
                FieldFilter(name=field_name, key=field_name if mapping["type"] != "text" else f"{field_name}.keyword")
            ]
        if "properties" in mapping:
            nested_fields = [
                cls._clean_property(nested_name + [name], value) for name, value in mapping["properties"].items()
            ]
            return reduce(add, nested_fields)
        return []


def instantiate_log_client(log_config: ElasticSearchConfig, bk_username: str) -> LogClientProtocol:
    """实例化 log client 实例"""
    if log_config.backend_type == "bkLog":
        assert log_config.bk_log_config
        return BKLogClient(log_config.bk_log_config, bk_username=bk_username)
    elif log_config.backend_type == "es":
        assert log_config.elastic_search_host
        return ESLogClient(log_config.elastic_search_host)
    raise NotImplementedError(f"unsupported backend_type<{log_config.backend_type}>")
