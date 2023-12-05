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
from typing import Dict, List, Protocol, Tuple

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from elasticsearch import Elasticsearch
from elasticsearch_dsl.aggs import DateHistogram
from elasticsearch_dsl.response import AggResponse, Response
from elasticsearch_dsl.response.aggs import FieldBucketData

from paasng.bk_plugins.pluginscenter.definitions import (
    BKLogConfig,
    ElasticSearchHost,
    PluginBackendAPIResource,
    PluginLogConfig,
)
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.log.constants import DEFAULT_LOG_BATCH_SIZE
from paasng.bk_plugins.pluginscenter.thirdparty.utils import make_client
from paasng.utils.es_log.misc import count_filters_options
from paasng.utils.es_log.models import FieldFilter
from paasng.utils.es_log.search import SmartSearch


class LogClientProtocol(Protocol):
    """LogClient protocol, all log search backend should abide this protocol"""

    def execute_search(self, index: str, search: SmartSearch, timeout: int) -> Tuple[Response, int]:
        """Search log from index with search"""

    def aggregate_date_histogram(self, index: str, search: SmartSearch, timeout: int) -> FieldBucketData:
        """Aggregate time-based histogram"""

    def aggregate_fields_filters(self, index: str, search: SmartSearch, timeout: int) -> List[FieldFilter]:
        """Aggregate fields filters"""


class BKLogClient:
    """BKLogClient is an implement of LogClientProtocol, the log search backend is bk log search"""

    def __init__(self, config: BKLogConfig, bk_username: str):
        self.config = config
        bk_log_stage = config.bkLogApiStage
        self.client = make_client(
            PluginBackendAPIResource(apiName="log-search", path="esquery_dsl/", method="POST", stage=bk_log_stage),
            bk_username=bk_username,
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

    def aggregate_date_histogram(self, index: str, search: SmartSearch, timeout: int) -> FieldBucketData:
        """Aggregate time-based histogram"""
        agg = DateHistogram(
            field=search.time_field,
            interval=search.time_range.detect_date_histogram_interval(),
            time_zone=settings.TIME_ZONE,
            min_doc_count=1,
        )
        search.search.aggs.bucket("histogram", agg)
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
        # 拉取最近 DEFAULT_LOG_BATCH_SIZE 条日志, 用于统计字段分布
        search = search.limit_offset(limit=DEFAULT_LOG_BATCH_SIZE, offset=0)
        data = {
            "indices": index,
            "scenario_id": self.config.scenarioID,
            "body": search.to_dict(),
        }
        resp = self._call_api(data, timeout)
        filters = {field: FieldFilter(name=field, key=field) for field in resp["data"]["select_fields_order"]}
        return count_filters_options(list(Response(search.search, resp["data"])), filters)

    def _call_api(self, data, timeout: int):
        if self.config.bkdataAuthenticationMethod:
            data["bkdata_authentication_method"] = self.config.bkdataAuthenticationMethod
        if self.config.bkdataDataToken:
            data["bkdata_data_token"] = self.config.bkdataDataToken
        return self.client.call(data=data, timeout=timeout)


class ESLogClient:
    """ESLogClient is an implement of LogClientProtocol, the log search backend is official elasticsearch"""

    def __init__(self, hosts: List[ElasticSearchHost]):
        self.hosts = hosts
        self._client = Elasticsearch(hosts=[host.dict() for host in hosts])

    def execute_search(self, index: str, search: SmartSearch, timeout: int) -> Tuple[Response, int]:
        """search log from index with body and params, implement with es client"""
        response = Response(
            search.search,
            self._client.search(body=search.to_dict(), index=index, params={"request_timeout": timeout}),
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
        search.search.aggs.bucket("histogram", agg)
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
        # 拉取最近 DEFAULT_LOG_BATCH_SIZE 条日志, 用于统计字段分布
        search = search.limit_offset(limit=DEFAULT_LOG_BATCH_SIZE, offset=0)
        response = Response(
            search.search,
            self._client.search(body=search.to_dict(), index=index, params={"request_timeout": timeout}),
        )
        return count_filters_options(list(response), self._get_properties_filters(index=index, timeout=timeout))

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
        if not all_mappings:
            raise error_codes.QUERY_ES_ERROR.f(
                _("No mappings available, maybe index does not exist or no logs at all")
            )
        first_mapping = all_mappings[sorted(all_mappings, reverse=True)[0]]
        docs_mappings: Dict = first_mapping["mappings"]
        return {f.name: f for f in self._clean_property([], docs_mappings)}

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


def instantiate_log_client(log_config: PluginLogConfig, bk_username: str) -> LogClientProtocol:
    """实例化 log client 实例"""
    if log_config.backendType == "bkLog":
        assert log_config.bkLogConfig
        return BKLogClient(log_config.bkLogConfig, bk_username=bk_username)
    elif log_config.backendType == "es":
        assert log_config.elasticSearchHosts
        return ESLogClient(log_config.elasticSearchHosts)
    raise NotImplementedError(f"unsupported backend_type<{log_config.backendType}>")
