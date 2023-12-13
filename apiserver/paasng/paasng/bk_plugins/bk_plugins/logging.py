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
import logging

"""Logging facilities for bk-plugins"""
import json
from typing import Any, Dict, Optional, Tuple

import cattr
from attrs import converters, define, field
from django.conf import settings

from paasng.accessories.log.client import LogClientProtocol, instantiate_log_client
from paasng.accessories.log.constants import DEFAULT_LOG_BATCH_SIZE
from paasng.accessories.log.filters import EnvFilter
from paasng.accessories.log.models import ElasticSearchConfig, ElasticSearchParams, ProcessLogQueryConfig
from paasng.accessories.log.shim import LogCollectorType, get_log_collector_type
from paasng.accessories.log.utils import clean_logs, get_es_term
from paasng.bk_plugins.bk_plugins.models import BkPlugin
from paasng.platform.applications.models import ModuleEnvironment
from paasng.utils.datetime import convert_timestamp_to_str
from paasng.utils.es_log.models import LogLine, Logs, extra_field, field_extractor_factory
from paasng.utils.es_log.search import SmartSearch
from paasng.utils.es_log.time_range import SmartTimeRange

logger = logging.getLogger(__name__)


@define
class StructureLogLine(LogLine):
    """结构化日志结构

    :param detail: alias of raw. This is the field before refactoring. It is kept for compatibility purposes.
    :param region: [deprecated] app region
    :param plugin_code: alais of app_code.
    :param environment: [deprecated] runtime environment(stag/prod), plugin app should on be "prod"
    :param process_id: process_id
    :param stream: stream, such as "django", "celery", "stdout"
    :param ts: [deprecated]datetime string, use timestamp(utc) instead
    """

    # extra useful field, will be extracted from the same field in raw
    detail: Dict[str, Any] = field(init=False)
    plugin_code: str = extra_field(source="app_code", converter=converters.optional(str))
    environment: str = extra_field(converter=converters.optional(str))
    process_id: Optional[str] = extra_field(converter=converters.optional(str))
    stream: Optional[str] = extra_field(
        source=field_extractor_factory(field_key="stream", raise_exception=False), converter=converters.optional(str)
    )
    ts: str = extra_field(converter=converters.optional(str))

    def __attrs_post_init__(self):
        self.detail = self.raw
        self.raw["ts"] = convert_timestamp_to_str(self.timestamp)
        # 适配 bk-sops 需要的日志字段, 将日志平台清洗后打平的字段扩展到 detail
        for src_filed, dest_field in [
            ("levelname", "json.levelname"),
            ("funcName", "json.funcName"),
            ("message", "json.message"),
        ]:
            if dest_field not in self.detail:
                try:
                    self.detail[dest_field] = self.detail[src_filed]
                except Exception:
                    logger.exception(
                        "failed to adaptor to bk-sops required log format, missing field `%s`", dest_field
                    )
        super().__attrs_post_init__()


class PluginLoggingClient:
    # Query logs in last 14 days by default
    _default_time_range = "14d"
    # Query "default" module because it is the only module bk_plugin applications have
    _module_name = "default"

    def __init__(self, bk_plugin: BkPlugin):
        """Create a logging client from bk_plugin object

        :param bk_plugin: The plugin object
        """
        self.application = bk_plugin.get_application()

    def query(self, trace_id: str, scroll_id: Optional[str] = None) -> Logs[StructureLogLine]:
        """Query logs

        :param trace_id: "trace_id" is an identifier for filtering logs
        :param scroll_id: id for scrolling logs
        """
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                index=log_config.search_params.indexPattern,
                time_range=SmartTimeRange(time_range=self._default_time_range),
                timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT,
            ),
            trace_id=trace_id,
        )

        response, total = log_client.execute_scroll_search(
            index=log_config.search_params.indexPattern,
            search=search,
            timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT,
            scroll_id=scroll_id,
        )
        logs = cattr.structure(
            {
                "logs": clean_logs(list(response), log_config.search_params),
                "total": total,
                "dsl": json.dumps(search.to_dict()),
                "scroll_id": response._scroll_id,
            },
            Logs[StructureLogLine],
        )
        return logs

    def instantiate_log_client(self) -> Tuple[LogClientProtocol, ElasticSearchConfig]:
        """初始化日志查询客户端"""
        # TODO: 统计 LOG_SEARCH_COUNTER 指标
        # LOG_SEARCH_COUNTER.labels(
        #     environment=request.GET.get('environment', 'all'), stream=request.GET.get('stream', 'all')
        # ).inc()
        module = self.application.get_module(module_name=self._module_name)
        log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(module.get_envs("prod")).json
        return instantiate_log_client(log_config=log_config, bk_username="blueking"), log_config

    def make_search(self, mappings: dict, trace_id: str) -> SmartSearch:
        """构造日志查询语句

        :param trace_id: "trace_id" is an identifier for filtering logs
        """
        module = self.application.get_module(module_name=self._module_name)
        # 插件应用只部署 prod 环境
        env = module.get_envs(environment="prod")
        smart_time_range = SmartTimeRange(time_range=self._default_time_range)
        query_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).json
        search = self._make_base_search(
            env=env, search_params=query_config.search_params, mappings=mappings, time_range=smart_time_range
        )

        if get_log_collector_type(env) == LogCollectorType.BK_LOG:
            # 日志平台方案会将未配置清洗规则的字段, 映射到 __ext_json 字段
            query_term = "__ext_json.trace_id"
            search = search.sort(
                {
                    "dtEventTimeStamp": {"order": "asc"},
                    "gseIndex": {"order": "asc"},
                    "iterationIndex": {"order": "asc"},
                }
            )
        else:
            # PaaS 内置采集方案会将所有字段放到 json 字段
            query_term = "json.trace_id"
        return search.filter("term", **{get_es_term(query_term=query_term, mappings=mappings): trace_id})

    def _make_base_search(
        self,
        env: ModuleEnvironment,
        search_params: ElasticSearchParams,
        mappings: dict,
        time_range: SmartTimeRange,
        limit: int = DEFAULT_LOG_BATCH_SIZE,
        offset: int = 0,
    ) -> SmartSearch:
        """构造基础的搜索语句, 包括过滤应用信息、时间范围、分页等"""
        plugin_filter = EnvFilter(env=env, search_params=search_params, mappings=mappings)
        # UPDATE: Use ascend order for querying plugin logs
        search = SmartSearch(time_field=search_params.timeField, time_range=time_range, time_order="asc")
        search = plugin_filter.filter_by_env(search)
        search = plugin_filter.filter_by_builtin_filters(search)
        search = plugin_filter.filter_by_builtin_excludes(search)
        return search.limit_offset(limit=limit, offset=offset)
