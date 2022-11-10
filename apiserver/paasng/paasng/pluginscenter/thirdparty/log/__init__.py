"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import json
import logging
from typing import Literal, Optional

import cattr

from paasng.pluginscenter.definitions import ElasticSearchParams
from paasng.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.pluginscenter.thirdparty.log.client import instantiate_log_client
from paasng.pluginscenter.thirdparty.log.filters import ElasticSearchFilter
from paasng.pluginscenter.thirdparty.log.models import (
    DateHistogram,
    IngressLogLine,
    Logs,
    StandardOutputLogLine,
    StructureLogLine,
    clean_histogram_buckets,
    clean_logs,
)
from paasng.pluginscenter.thirdparty.log.search import SmartSearch
from paasng.pluginscenter.thirdparty.log.utils import SmartTimeRange

logger = logging.getLogger(__name__)


DEFAULT_ES_SEARCH_TIMEOUT = 30


def query_standard_output_logs(
    pd: PluginDefinition,
    instance: PluginInstance,
    operator: str,
    time_range: SmartTimeRange,
    query_string: str,
    limit: int,
    offset: int,
) -> Logs[StandardOutputLogLine]:
    """查询标准输出日志"""
    log_client = instantiate_log_client(pd.log_config, operator)
    stdout_config = pd.log_config.stdout
    search = make_base_search(
        plugin=instance, search_params=stdout_config, time_range=time_range, limit=limit, offset=offset
    )
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    response, total = log_client.execute_search(
        index=stdout_config.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            "logs": clean_logs(list(response), stdout_config),
            "total": total,
            "dsl": json.dumps(search.to_dict()),
        },
        Logs[StandardOutputLogLine],
    )


def query_structure_logs(
    pd: PluginDefinition,
    instance: PluginInstance,
    operator: str,
    time_range: SmartTimeRange,
    query_string: str,
    limit: int,
    offset: int,
) -> Logs[StructureLogLine]:
    """查询结构化日志"""
    log_client = instantiate_log_client(pd.log_config, operator)
    json_config = pd.log_config.json_
    if not json_config:
        raise ValueError("this plugin does not support query json logs")
    search = make_base_search(
        plugin=instance, search_params=json_config, time_range=time_range, limit=limit, offset=offset
    )
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    response, total = log_client.execute_search(
        index=json_config.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            "logs": clean_logs(list(response), json_config),
            "total": total,
            "dsl": json.dumps(search.to_dict()),
        },
        Logs[StructureLogLine],
    )


def query_ingress_logs(
    pd: PluginDefinition,
    instance: PluginInstance,
    operator: str,
    time_range: SmartTimeRange,
    query_string: str,
    limit: int,
    offset: int,
) -> Logs[IngressLogLine]:
    """查询 ingress 访问日志"""
    log_client = instantiate_log_client(pd.log_config, operator)
    ingress_config = pd.log_config.ingress
    if not ingress_config:
        raise ValueError("this plugin does not support query ingress logs")
    search = make_base_search(
        plugin=instance, search_params=ingress_config, time_range=time_range, limit=limit, offset=offset
    )
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    response, total = log_client.execute_search(
        index=ingress_config.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            "logs": clean_logs(list(response), ingress_config),
            "total": total,
            "dsl": json.dumps(search.to_dict()),
        },
        Logs[IngressLogLine],
    )


def aggregate_date_histogram(
    pd: PluginDefinition,
    instance: PluginInstance,
    log_type: Literal["standard_output", "structure", "ingress"],
    operator: str,
    time_range: SmartTimeRange,
    query_string: str,
) -> DateHistogram:
    """查询日志的直方图"""
    log_client = instantiate_log_client(pd.log_config, operator)
    search_params: Optional[ElasticSearchParams] = None
    if log_type == "standard_output":
        search_params = pd.log_config.stdout
    elif log_type == "structure":
        search_params = pd.log_config.json_
    elif log_type == "ingress":
        search_params = pd.log_config.ingress
    if not search_params:
        raise ValueError(f"this plugin does not support query {log_type} logs")
    search = make_base_search(plugin=instance, search_params=search_params, time_range=time_range, limit=0, offset=0)
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    response = log_client.aggregate_date_histogram(
        index=search_params.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            **clean_histogram_buckets(response),
            "dsl": json.dumps(search.to_dict()),
        },
        DateHistogram,
    )


def make_base_search(
    plugin: PluginInstance,
    search_params: ElasticSearchParams,
    time_range: SmartTimeRange,
    limit: int = 200,
    offset: int = 0,
) -> SmartSearch:
    """生成基础的搜索语句, 包括过滤插件id、时间范围、分页等"""
    plugin_filter = ElasticSearchFilter(plugin=plugin, search_params=search_params)
    search = SmartSearch(time_field=search_params.timeField, time_range=time_range)
    search = plugin_filter.filter_by_plugin(search)
    search = plugin_filter.filter_by_builtin_filters(search)
    search = plugin_filter.filter_by_builtin_excludes(search)
    return search.limit_offset(limit=limit, offset=offset)
