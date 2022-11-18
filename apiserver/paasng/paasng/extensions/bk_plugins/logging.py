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
from typing import Dict, List, Optional

from django.conf import settings
from elasticsearch_dsl.response import Response as ESResponse
from pydantic import BaseModel, Field

from paasng.platform.log.client import LogClient, SmartTimeRange
from paasng.platform.log.filters import AppLogFilter
from paasng.platform.log.models import LogLine, LogPage, SimpleDomainSpecialLanguage

from .models import BkPlugin


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

    def query(self, trace_id: str, scroll_id: Optional[str] = None) -> 'BkPluginLogs':
        """Query logs

        :param trace_id: "trace_id" is an identifier for filtering logs
        :param scroll_id: id for scrolling logs
        """
        client = self.make_client()
        # The `trace_id` must be wrapped with a list to make LogClient's API happy
        client.query_conditions.add_terms_conditions(**{'json.trace_id': [trace_id]})
        return client.query_scrollable_logs(scroll_id, result_type=BkPluginLogs.new)

    def make_client(self) -> LogClient:
        """Make a LogClient object for making queries"""
        app_filter = self._make_app_filter()
        client = LogClient(
            app_filter=app_filter,
            query_conditions=SimpleDomainSpecialLanguage(query={}),
            smart_time_range=SmartTimeRange(time_range=self._default_time_range),
            index_pattern=settings.ES_K8S_LOG_INDEX_PATTERNS,
            log_page_class=LogPage,
        )

        # Ignore stdout/stderr logs
        client.query_conditions.add_exclude_conditions(stream=["stderr", "stdout"])
        return client

    def _make_app_filter(self) -> AppLogFilter:
        """Make filter object for query"""
        app_filter = AppLogFilter(
            region=self.application.region, app_code=self.application.code, module_name=self._module_name
        )
        return app_filter


class LogEntry(BaseModel):
    """A bk_plugin log entry object. Similar with `LogLine`, some fields were removed."""

    # Adapts the field name in raw log data because bk_plugin only have "code"， not "app_code"
    plugin_code: str = Field(..., alias='app_code')
    environment: str
    process_id: str
    stream: str
    message: str
    detail: Dict
    ts: str


class BkPluginLogs(BaseModel):
    """A collection type for storing bk_plugin's structured logs"""

    scroll_id: str
    logs: List[LogEntry]
    total: int = 0

    @classmethod
    def new(cls, scroll_id: str, logs: ESResponse, total: int) -> 'BkPluginLogs':
        """A factory method for handling data from LogClient"""
        log_items = []
        for log in logs:
            # Parsed with original structured parse first, then transform to LogEntry
            _log = LogLine.parse_from_es_log(log)
            log_items.append(LogEntry.parse_obj(_log))
        return BkPluginLogs(scroll_id=scroll_id, logs=log_items, total=total)
