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
from operator import add
from typing import Dict, List, Optional, Protocol, Tuple

from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import ScanError
from elasticsearch_dsl.aggs import DateHistogram
from elasticsearch_dsl.response import AggResponse, Response
from elasticsearch_dsl.response.aggs import FieldBucketData

from paasng.platform.log.filters import FieldFilter, count_filters_options
from paasng.platform.log.models import BKLogConfig, ElasticSearchConfig, ElasticSearchHost

# TODO: 避免引用插件开发中心的代码, 提取通用组件
from paasng.pluginscenter.definitions import PluginBackendAPIResource
from paasng.pluginscenter.thirdparty.utils import make_client
from paasng.utils.es_log.search import SmartSearch


class LogClientProtocol(Protocol):
    """LogClient protocol, all log search backend should abide this protocol"""

    def execute_search(self, index: str, search: SmartSearch, timeout: int) -> Tuple[Response, int]:
        """search log from index with search"""

    def execute_scroll_search(
        self, index: str, search: SmartSearch, timeout: int, scroll_id: Optional[str] = None, scroll="5m"
    ) -> Tuple[Response, int]:
        """search log(scrolling) from index with search"""

    def aggregate_date_histogram(self, index: str, search: SmartSearch, timeout: int) -> FieldBucketData:
        """aggregate time-based histogram"""

    def aggregate_fields_filters(self, index: str, search: SmartSearch, timeout: int) -> List[FieldFilter]:
        """aggregate fields filters"""

    def get_mappings(self, index: str, timeout: int) -> dict:
        """query the mappings in es"""


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
        """aggregate time-based histogram"""
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

    def aggregate_fields_filters(self, index: str, search: SmartSearch, timeout: int) -> List[FieldFilter]:
        """aggregate fields filter"""
        # 拉取最近 200 条日志, 用于统计字段分布
        search = search.limit_offset(limit=200, offset=0)
        data = {
            "indices": index,
            "scenario_id": self.config.scenarioID,
            "body": search.to_dict(),
        }
        resp = self._call_api(data, timeout)
        filters = {field: FieldFilter(name=field, key=field) for field in resp["data"]["select_fields_order"]}
        return count_filters_options(list(Response(search.search, resp["data"])), filters)

    def get_mappings(self, index: str, timeout: int) -> dict:
        """query the mappings in es"""
        raise NotImplementedError("TODO: 确认日志平台接口 /esquery_mapping/ 是否可用")

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
        response = Response(
            search.search,
            self._client.search(body=search.to_dict(), index=index, params={"request_timeout": timeout}),
        )
        return (response, self._get_response_count(index, search, timeout, response))

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
            response = Response(
                search.search,
                self._client.search(
                    body=search.to_dict(), scroll=scroll, index=index, params={"request_timeout": timeout}
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
        """aggregate time-based histogram"""
        agg = DateHistogram(
            field=search.time_field,
            interval=search.time_range.detect_date_histogram_interval(),
            time_zone=settings.TIME_ZONE,
            min_doc_count=1,
        )
        search.search.aggs.bucket('histogram', agg)
        search.limit_offset(0, 0)
        return AggResponse(
            search.search.aggs,
            search.search,
            self._client.search(body=search.to_dict(), index=index, params={"request_timeout": timeout})[
                "aggregations"
            ],
        ).histogram

    def aggregate_fields_filters(self, index: str, search: SmartSearch, timeout: int) -> List[FieldFilter]:
        """aggregate fields filter"""
        # 拉取最近 200 条日志, 用于统计字段分布
        search = search.limit_offset(limit=200, offset=0)
        response = Response(
            search.search,
            self._client.search(body=search.to_dict(), index=index, params={"request_timeout": timeout}),
        )
        return count_filters_options(list(response), self._get_properties_filters(index=index, timeout=timeout))

    def get_mappings(self, index: str, timeout: int) -> dict:
        """query the mappings in es"""
        all_mappings = self._client.indices.get_mapping(index, params={"request_timeout": timeout})
        first_mapping = all_mappings[sorted(all_mappings, reverse=True)[0]]
        docs_mappings: Dict = first_mapping["mappings"]
        return docs_mappings

    def _get_response_count(self, index: str, search: SmartSearch, timeout: int, response: Response) -> int:
        """get total field from es response if it had, or send a count response to es"""
        if response.hits.total.relation == "eq":
            return response.hits.total.value
        return self._client.count(body=search.to_dict(count=True), index=index, params={"request_timeout": timeout})[
            "count"
        ]

    def _get_properties_filters(self, index: str, timeout: int) -> Dict[str, FieldFilter]:
        """获取属性映射"""
        # 当前假设同一批次的 index(类似 aa-2021.04.20,aa-2021.04.19) 拥有相同的 mapping, 因此直接获取最新的 mapping
        # 如果同一批次 index mapping 发生变化，可能会导致日志查询为空
        all_mappings = self._client.indices.get_mapping(index, params={"request_timeout": timeout})
        first_mapping = all_mappings[sorted(all_mappings, reverse=True)[0]]
        docs_mappings: Dict = first_mapping["mappings"]
        return {f.name: f for f in self._clean_property([], docs_mappings)}

    def _clean_property(self, nested_name: List[str], mapping: Dict) -> List[FieldFilter]:
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
                self._clean_property(nested_name + [name], value) for name, value in mapping["properties"].items()
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
