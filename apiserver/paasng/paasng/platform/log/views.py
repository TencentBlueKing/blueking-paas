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
from typing import ClassVar, List, Optional, Type

import cattr
from django.conf import settings
from django.utils.translation import gettext as _
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import ScanError
from pydantic import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.viewsets import ViewSet

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_required
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log import serializers
from paasng.platform.log.client import instantiate_log_client
from paasng.platform.log.constants import LogType
from paasng.platform.log.dsl import SimpleDomainSpecialLanguage
from paasng.platform.log.filters import ElasticSearchFilter
from paasng.platform.log.models import ElasticSearchParams, ProcessLogQueryConfig
from paasng.platform.log.responses import IngressLogLine, StandardOutputLogLine, StructureLogLine
from paasng.platform.log.utils import clean_logs, parse_simple_dsl_to_dsl
from paasng.utils.error_codes import error_codes
from paasng.utils.es_log.misc import clean_histogram_buckets
from paasng.utils.es_log.models import DateHistogram, Logs
from paasng.utils.es_log.search import SmartSearch
from paasng.utils.es_log.time_range import SmartTimeRange

logger = logging.getLogger(__name__)


class LogBaseAPIView(ViewSet, ApplicationCodeInPathMixin):
    log_type: LogType
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def instantiate_log_client(self):
        """初始化日志查询客户端"""
        # TODO: 统计 LOG_SEARCH_COUNTER 指标
        # LOG_SEARCH_COUNTER.labels(
        #     environment=request.GET.get('environment', 'all'), stream=request.GET.get('stream', 'all')
        # ).inc()
        env = self.get_env_via_path()
        log_config = self._get_log_query_config(env, process_type=self.request.query_params.get("process_type"))
        return instantiate_log_client(log_config=log_config, bk_username=self.request.user.username), log_config

    def make_search(self, mappings: dict):
        """构造日志查询语句"""
        env = self.get_env_via_path()
        params = self.request.query_params
        smart_time_range = SmartTimeRange(
            time_range=params["time_range"], start_time=params.get("start_time"), end_time=params.get("end_time")
        )
        query_config = self._get_log_query_config(env, process_type=params.get("process_type"))
        search = self._make_base_search(env, search_params=query_config.search_params, time_range=smart_time_range)

        if self.request.data:
            try:
                query_conditions = SimpleDomainSpecialLanguage(**self.request.data)
            except ValidationError:
                logger.exception("error log query conditions")
                raise error_codes.QUERY_REQUEST_ERROR
            dsl = parse_simple_dsl_to_dsl(query_conditions, mappings=mappings)
            search = search.query(dsl)
        return search

    def _make_base_search(
        self,
        env: ModuleEnvironment,
        search_params: ElasticSearchParams,
        time_range: SmartTimeRange,
        limit: int = 200,
        offset: int = 0,
    ) -> SmartSearch:
        """构造基础的搜索语句, 包括过滤应用信息、时间范围、分页等"""
        plugin_filter = ElasticSearchFilter(env=env, search_params=search_params)
        search = SmartSearch(time_field=search_params.timeField, time_range=time_range)
        search = plugin_filter.filter_by_env(search)
        search = plugin_filter.filter_by_builtin_filters(search)
        search = plugin_filter.filter_by_builtin_excludes(search)
        return search.limit_offset(limit=limit, offset=offset)

    def _get_log_query_config(self, env: ModuleEnvironment, process_type: Optional[str] = None):
        """获取日志查询配置"""
        log_type = self.log_type
        if log_type == LogType.INGRESS:
            log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).ingress
        elif log_type == LogType.STANDARD_OUTPUT:
            log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).stdout
        else:
            if process_type is None:
                raise ValueError("structured log must provide `process_type` field")
            log_config = ProcessLogQueryConfig.objects.get_by_process_type(process_type=process_type, env=env).json
        return log_config


class LogAPIView(LogBaseAPIView):
    line_model: ClassVar[Type]
    logs_serializer_class: ClassVar[Type[Serializer]]

    def query_logs(self, request, code, module_name):
        """查询日志"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            )
        )

        try:
            response, total = log_client.execute_search(
                index=log_config.search_params.indexPattern, search=search, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            )
        except RequestError:
            raise error_codes.QUERY_REQUEST_ERROR
        except Exception:
            logger.exception("failed to get logs")
            raise error_codes.QUERY_LOG_FAILED.f(_('日志查询失败，请稍后再试。'))

        logs = cattr.structure(
            {
                "logs": clean_logs(list(response), log_config.search_params),
                "total": total,
                "dsl": json.dumps(search.to_dict()),
            },
            Logs[self.line_model],  # type: ignore
        )
        return Response(data=self.logs_serializer_class(logs).data)

    def aggregate_date_histogram(self, request, code, module_name):
        """统计日志的日志数-事件直方图"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            )
        )

        response = log_client.aggregate_date_histogram(
            index=log_config.search_params.indexPattern, search=search, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
        )
        date_histogram = cattr.structure(
            {
                **clean_histogram_buckets(response),
                "dsl": json.dumps(search.to_dict()),
            },
            DateHistogram,
        )
        return Response(data=serializers.DateHistogramSLZ(date_histogram).data)

    def aggregate_fields_filters(self, request, code, module_name):
        """统计日志的字段分布"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            )
        )

        fields_filters = log_client.aggregate_fields_filters(
            index=log_config.search_params.indexPattern, search=search, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
        )
        return Response(data=serializers.LogFieldFilterSLZ(fields_filters, many=True).data)


class StdoutLogAPIView(LogAPIView):
    # TODO: 支持根据 scroll id 查询
    line_model = StandardOutputLogLine
    log_type = LogType.STANDARD_OUTPUT
    logs_serializer_class = serializers.StandardOutputLogsSLZ

    def query_logs_scroll(self, request, code, module_name):
        """查询标准输出日志"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(mappings={})

        try:
            response, total = log_client.execute_search(
                index=log_config.search_params.indexPattern, search=search, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            )
        except ScanError:
            # scan 失败大概率是 scroll_id 失效
            logger.exception("scroll_id 失效, 日志查询失败")
            raise error_codes.QUERY_LOG_FAILED.f(_('日志查询快照失效, 请刷新后重试。'))
        except RequestError:
            raise error_codes.QUERY_REQUEST_ERROR
        except Exception:
            logger.exception("failed to get logs")
            raise error_codes.QUERY_LOG_FAILED.f(_('日志查询失败，请稍后再试。'))

        logs = cattr.structure(
            {
                "logs": clean_logs(list(response), log_config.search_params),
                "total": total,
                "dsl": json.dumps(search.to_dict()),
                # TODO: 设置 scroll_id
                "scroll_id": "TODO",
            },
            Logs[self.line_model],  # type: ignore
        )
        return Response(data=self.logs_serializer_class(logs).data)


class StructuredLogAPIView(LogAPIView):
    line_model = StructureLogLine
    log_type = LogType.STRUCTURED
    logs_serializer_class = serializers.StructureLogsSLZ


class IngressLogAPIView(LogAPIView):
    line_model = IngressLogLine
    log_type = LogType.INGRESS
    logs_serializer_class = serializers.IngressLogSLZ


class SysStructuredLogAPIView(StructuredLogAPIView):
    permission_classes: List = []

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_logs(self, request, code, module_name):
        return super().query_logs(request, code, module_name)
