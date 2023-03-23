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
"""Logging facilities for bk-plugins"""
import json
from typing import Any, Dict, Optional

import cattr
from attrs import converters, define, field, fields
from django.conf import settings

from paasng.extensions.bk_plugins.models import BkPlugin
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log.client import instantiate_log_client
from paasng.platform.log.filters import EnvFilter
from paasng.platform.log.models import ElasticSearchParams, ProcessLogQueryConfig
from paasng.platform.log.utils import clean_logs
from paasng.utils.es_log.models import Logs
from paasng.utils.es_log.search import SmartSearch
from paasng.utils.es_log.time_range import SmartTimeRange


@define
class StructureLogLine:
    """结构化日志结构"""

    timestamp: int
    message: str

    # key: json.*
    # e.g. json.funcName
    detail: Dict[str, Any]

    region: str
    plugin_code: str = field(init=False, converter=converters.optional(str))
    environment: str
    process_id: Optional[str]

    def __attrs_post_init__(self):
        for attr in fields(type(self)):
            if not attr.init:
                setattr(self, attr.name, self.detail.get(attr.name))


class PluginLoggingClient:

    # Query logs in last 14 days by default
    _default_time_range = '14d'
    # Query "default" module because it is the only module bk_plugin applications have
    _module_name = 'default'

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
        search = self.make_search(trace_id)

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

    def instantiate_log_client(self):
        """初始化日志查询客户端"""
        # TODO: 统计 LOG_SEARCH_COUNTER 指标
        # LOG_SEARCH_COUNTER.labels(
        #     environment=request.GET.get('environment', 'all'), stream=request.GET.get('stream', 'all')
        # ).inc()
        module = self.application.get_module(module_name=self._module_name)
        log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(module)
        return instantiate_log_client(log_config=log_config, bk_username="blueking"), log_config

    def make_search(self, trace_id: str) -> SmartSearch:
        """构造日志查询语句"""
        module = self.application.get_module(module_name=self._module_name)
        env = module.get_envs(environment="prod")
        smart_time_range = SmartTimeRange(time_range=self._default_time_range)
        query_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env)
        search = self._make_base_search(env=env, search_params=query_config.search_params, time_range=smart_time_range)
        return search.filter(**{'json.trace_id': [trace_id]})

    def _make_base_search(
        self,
        env: ModuleEnvironment,
        search_params: ElasticSearchParams,
        time_range: SmartTimeRange,
        limit: int = 200,
        offset: int = 0,
    ) -> SmartSearch:
        """构造基础的搜索语句, 包括过滤应用信息、时间范围、分页等"""
        plugin_filter = EnvFilter(env=env, search_params=search_params)
        search = SmartSearch(time_field=search_params.timeField, time_range=time_range)
        search = plugin_filter.filter_by_env(search)
        search = plugin_filter.filter_by_builtin_filters(search)
        search = plugin_filter.filter_by_builtin_excludes(search)
        return search.limit_offset(limit=limit, offset=offset)
