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
import json
import logging
from typing import Dict, List, Literal, Optional, Tuple, cast

import cattr

from paasng.accessories.log.constants import LogType
from paasng.accessories.log.models import ProcessLogQueryConfig
from paasng.bk_plugins.pluginscenter.definitions import ElasticSearchParams
from paasng.bk_plugins.pluginscenter.log.client import LogClientProtocol, instantiate_log_client
from paasng.bk_plugins.pluginscenter.log.filters import ElasticSearchFilter
from paasng.bk_plugins.pluginscenter.log.responses import IngressLogLine, StandardOutputLogLine, StructureLogLine
from paasng.bk_plugins.pluginscenter.log.utils import clean_logs
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.platform.applications.models import Application
from paasng.utils.es_log.misc import clean_histogram_buckets
from paasng.utils.es_log.models import DateHistogram, FieldFilter, Logs
from paasng.utils.es_log.search import SmartSearch
from paasng.utils.es_log.time_range import SmartTimeRange

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
    log_client, search_params = _instantiate_log_client(pd, instance, LogType.STANDARD_OUTPUT, operator)
    search = make_base_search(
        plugin=instance, search_params=search_params, time_range=time_range, limit=limit, offset=offset
    )
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    response, total = log_client.execute_search(
        index=search_params.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            "logs": clean_logs(list(response), search_params),
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
    terms: Optional[Dict[str, List[str]]] = None,
    exclude: Optional[Dict[str, List[str]]] = None,
) -> Logs[StructureLogLine]:
    """查询结构化日志"""
    log_client, search_params = _instantiate_log_client(pd, instance, LogType.STRUCTURED, operator)
    search = make_base_search(
        plugin=instance, search_params=search_params, time_range=time_range, limit=limit, offset=offset
    )
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    if terms:
        search = search.filter("terms", **terms)
    if exclude:
        search = search.exclude("terms", **exclude)
    response, total = log_client.execute_search(
        index=search_params.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            "logs": clean_logs(list(response), search_params),
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
    log_client, search_params = _instantiate_log_client(pd, instance, LogType.INGRESS, operator)
    search = make_base_search(
        plugin=instance, search_params=search_params, time_range=time_range, limit=limit, offset=offset
    )
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    response, total = log_client.execute_search(
        index=search_params.indexPattern, search=search, timeout=DEFAULT_ES_SEARCH_TIMEOUT
    )
    return cattr.structure(
        {
            "logs": clean_logs(list(response), search_params),
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
    terms: Optional[Dict[str, List[str]]] = None,
    exclude: Optional[Dict[str, List[str]]] = None,
) -> DateHistogram:
    """查询日志的直方图"""
    # 前端在路径参数中使用了小写, 这里需要转换一下
    log_type_map = {
        "standard_output": LogType.STANDARD_OUTPUT,
        "structure": LogType.STRUCTURED,
        "ingress": LogType.INGRESS,
    }
    log_client, search_params = _instantiate_log_client(pd, instance, log_type_map[log_type], operator)

    search = make_base_search(plugin=instance, search_params=search_params, time_range=time_range, limit=0, offset=0)
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    if terms:
        search = search.filter("terms", **terms)
    if exclude:
        search = search.exclude("terms", **exclude)

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


def aggregate_fields_filters(
    pd: PluginDefinition,
    instance: PluginInstance,
    log_type: Literal["standard_output", "structure", "ingress"],
    operator: str,
    time_range: SmartTimeRange,
    query_string: str,
    terms: Optional[Dict[str, List[str]]] = None,
    exclude: Optional[Dict[str, List[str]]] = None,
) -> List[FieldFilter]:
    """查询日志的可选字段和对应的值分布(只取前200条数据做统计)"""
    # 前端在路径参数中使用了小写, 这里需要转换一下
    log_type_map = {
        "standard_output": LogType.STANDARD_OUTPUT,
        "structure": LogType.STRUCTURED,
        "ingress": LogType.INGRESS,
    }
    log_client, search_params = _instantiate_log_client(pd, instance, log_type_map[log_type], operator)

    search = make_base_search(plugin=instance, search_params=search_params, time_range=time_range, limit=200, offset=0)
    if query_string:
        search = search.filter("query_string", query=query_string, analyze_wildcard=True)
    if terms:
        search = search.filter("terms", **terms)
    if exclude:
        search = search.exclude("terms", **exclude)
    return log_client.aggregate_fields_filters(
        index=search_params.indexPattern,
        search=search,
        timeout=DEFAULT_ES_SEARCH_TIMEOUT,
        fields=search_params.filterFields,
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


def _instantiate_log_client(
    pd: PluginDefinition, instance: PluginInstance, log_type: LogType, operator: str
) -> Tuple[LogClientProtocol, ElasticSearchParams]:
    """实例化日志查询客户端"""
    if pd.identifier != "bk-saas":
        log_client = instantiate_log_client(pd.log_config, operator)
        search_params: ElasticSearchParams
        if log_type == LogType.STANDARD_OUTPUT:
            search_params = pd.log_config.stdout
        elif log_type == LogType.STRUCTURED:
            if not pd.log_config.json_:
                raise ValueError("this plugin does not support query json logs")
            search_params = cast(ElasticSearchParams, pd.log_config.json_)
        else:
            if not pd.log_config.ingress:
                raise ValueError("this plugin does not support query ingress logs")
            search_params = cast(ElasticSearchParams, pd.log_config.ingress)
        return log_client, search_params
    # 由于 bk-saas 接入了日志平台, 每个应用独立的日志查询配置, 因此需要访问 PaaS 的数据库获取配置信息
    env = Application.objects.get(code=instance.id).get_app_envs("prod")
    if log_type == LogType.INGRESS:
        log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).ingress
    elif log_type == LogType.STANDARD_OUTPUT:
        log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).stdout
    else:
        log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env=env).json
    # Note: log_config.search_params 返回的是 paasng.accessories.log.models.ElasticSearchParams
    # 该模型除了没有 filterFields 字段, 其他与插件开发中心的 ElasticSearchParams 一致,
    return instantiate_log_client(log_config, operator), log_config.search_params


def get_filter_fields(pd: PluginDefinition, log_type: LogType) -> List[str]:
    """获取插件类型中声明的字段列表"""
    search_params: ElasticSearchParams
    if log_type == LogType.STANDARD_OUTPUT:
        search_params = pd.log_config.stdout
    elif log_type == LogType.STRUCTURED:
        if not pd.log_config.json_:
            raise ValueError("this plugin does not support query json logs")
        search_params = cast(ElasticSearchParams, pd.log_config.json_)
    else:
        if not pd.log_config.ingress:
            raise ValueError("this plugin does not support query ingress logs")
        search_params = cast(ElasticSearchParams, pd.log_config.ingress)
    return search_params.filterFields
