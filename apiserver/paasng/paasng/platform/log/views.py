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
import re
from typing import TYPE_CHECKING, ClassVar, List, Optional, Tuple, Type

import cattr
from django.conf import settings
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
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
from paasng.platform.log.constants import DEFAULT_LOG_BATCH_SIZE, LogType
from paasng.platform.log.dsl import SearchRequestSchema
from paasng.platform.log.filters import EnvFilter, ModuleFilter
from paasng.platform.log.models import ElasticSearchParams, ProcessLogQueryConfig
from paasng.platform.log.responses import IngressLogLine, StandardOutputLogLine, StructureLogLine
from paasng.platform.log.shim import setup_env_log_model
from paasng.platform.log.utils import clean_logs, parse_request_to_es_dsl
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
        log_config = self._get_log_query_config(process_type=self.request.query_params.get("process_type"))
        return instantiate_log_client(log_config=log_config, bk_username=self.request.user.username), log_config

    def make_search(self, mappings: dict, time_field: str, highlight_fields: Optional[Tuple] = None):
        """构造日志查询语句

        :param mappings: ES mappings
        :param time_field: ES 时间字段, 默认根据 time_field 排序
        :param highlight_fields: 字段高亮规则
        """
        params = self.request.query_params
        smart_time_range = SmartTimeRange(
            time_range=params["time_range"], start_time=params.get("start_time"), end_time=params.get("end_time")
        )
        query_config = self._get_log_query_config(process_type=params.get("process_type"))
        search = self._make_base_search(
            search_params=query_config.search_params, time_range=smart_time_range, mappings=mappings
        )

        highlight_query = {}
        if self.request.data:
            try:
                query_conditions = SearchRequestSchema(**self.request.data)
            except ValidationError:
                logger.exception("error log query conditions")
                raise error_codes.QUERY_REQUEST_ERROR
            dsl = parse_request_to_es_dsl(query_conditions, mappings=mappings)
            highlight_query = dsl.to_dict()
            search = search.query(dsl)

            # 除非指定了 time_field 的排序规则, 否则总是按照 desc 排序
            sort_params = {time_field: {"order": "desc"}}
            if query_conditions.sort:
                sort_params.update({k: {"order": v} for k, v in query_conditions.sort.items()})
            search = search.sort(sort_params)

        # 顺序很重要, querystring 在 simple dsl 里, highlight_fields 必须在 search.query(dsl) 后面
        if highlight_query and highlight_fields:
            search = search.highlight(*highlight_fields, highlight_query=highlight_query)
        return search

    def _make_base_search(
        self,
        search_params: ElasticSearchParams,
        mappings: dict,
        time_range: SmartTimeRange,
        limit: int = DEFAULT_LOG_BATCH_SIZE,
        offset: int = 0,
    ) -> SmartSearch:
        """构造基础的搜索语句, 包括过滤应用信息、时间范围、分页等"""
        env = self.get_env_via_path()
        # 需要根据 mappings 来确定字段查询条件是否需要加 keyword
        es_filter = EnvFilter(env=env, search_params=search_params, mappings=mappings)
        search = SmartSearch(time_field=search_params.timeField, time_range=time_range)
        search = es_filter.filter_by_env(search)
        search = es_filter.filter_by_builtin_filters(search)
        search = es_filter.filter_by_builtin_excludes(search)
        return search.limit_offset(limit=limit, offset=offset)

    def _get_log_query_config(self, process_type: Optional[str] = None):
        """获取日志查询配置"""
        env = self.get_env_via_path()
        log_type = self.log_type
        if log_type == LogType.INGRESS:
            log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).ingress
        elif log_type == LogType.STANDARD_OUTPUT:
            log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).stdout
        else:
            try:
                log_config = ProcessLogQueryConfig.objects.get_by_process_type(process_type=process_type, env=env).json
            except ProcessLogQueryConfig.DoesNotExist:
                raise ValueError("structured log must provide `process_type` field")
        return log_config


class LogAPIView(LogBaseAPIView):
    line_model: ClassVar[Type]
    logs_serializer_class: ClassVar[Type[Serializer]]

    @swagger_auto_schema(
        query_serializer=serializers.LogQueryParamsSLZ,
        request_body=serializers.LogQueryBodySLZ,
    )
    def query_logs(self, request, code, module_name, environment):
        """查询日志"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            ),
            time_field=log_config.search_params.timeField,
            highlight_fields=("*", "*.*"),
        )

        try:
            response, total = log_client.execute_search(
                index=log_config.search_params.indexPattern,
                search=search,
                timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT,
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

    @swagger_auto_schema(
        query_serializer=serializers.LogQueryParamsSLZ,
        request_body=serializers.LogQueryBodySLZ,
    )
    def query_logs_scroll(self, request, code, module_name, environment):
        """查询标准输出日志"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            ),
            time_field=log_config.search_params.timeField,
            highlight_fields=(log_config.search_params.messageField,),
        )

        try:
            response, total = log_client.execute_scroll_search(
                index=log_config.search_params.indexPattern,
                search=search,
                timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT,
                scroll_id=request.query_params.get("scroll_id"),
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
                "scroll_id": response._scroll_id,
            },
            Logs[self.line_model],  # type: ignore
        )
        return Response(data=self.logs_serializer_class(logs).data)

    @swagger_auto_schema(
        query_serializer=serializers.LogQueryParamsSLZ,
        request_body=serializers.LogQueryBodySLZ,
    )
    def aggregate_date_histogram(self, request, code, module_name, environment):
        """统计日志的日志数-事件直方图"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            ),
            time_field=log_config.search_params.timeField,
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

    @swagger_auto_schema(
        query_serializer=serializers.LogQueryParamsSLZ,
        request_body=serializers.LogQueryBodySLZ,
    )
    def aggregate_fields_filters(self, request, code, module_name, environment):
        """统计日志的字段分布"""
        log_client, log_config = self.instantiate_log_client()
        search = self.make_search(
            mappings=log_client.get_mappings(
                log_config.search_params.indexPattern, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
            ),
            time_field=log_config.search_params.timeField,
        )

        fields_filters = log_client.aggregate_fields_filters(
            index=log_config.search_params.indexPattern, search=search, timeout=settings.DEFAULT_ES_SEARCH_TIMEOUT
        )
        if log_config.search_params.filedMatcher:
            matcher = re.compile(log_config.search_params.filedMatcher)
            fields_filters = [f for f in fields_filters if matcher.fullmatch(f.name)]
        return Response(data=serializers.LogFieldFilterSLZ(fields_filters, many=True).data)


class StdoutLogAPIView(LogAPIView):
    # TODO: 支持根据 scroll id 查询
    line_model = StandardOutputLogLine
    log_type = LogType.STANDARD_OUTPUT
    logs_serializer_class = serializers.StandardOutputLogsSLZ


class StructuredLogAPIView(LogAPIView):
    line_model = StructureLogLine
    log_type = LogType.STRUCTURED
    logs_serializer_class = serializers.StructureLogsSLZ


class IngressLogAPIView(LogAPIView):
    line_model = IngressLogLine
    log_type = LogType.INGRESS
    logs_serializer_class = serializers.IngressLogSLZ


if TYPE_CHECKING:
    _MixinBase = LogAPIView
else:
    _MixinBase = object


class LegacyLogAPIMixin(_MixinBase):
    # LegacyLogAPIMixin 是支持按模块查询日志的兼容性代码
    # 由于日志查询的重构复杂度高, 要求一步到位完全重构成按环境查询需要较长的排期
    # 待前端按照新接口(环境维度)重构后, 删除 legacy api
    def query_logs(self, request, code, module_name, environment=None):
        return super().query_logs(request, code, module_name, environment)

    def query_logs_scroll(self, request, code, module_name, environment=None):
        return super().query_logs_scroll(request, code, module_name, environment)

    def aggregate_date_histogram(self, request, code, module_name, environment=None):
        return super().aggregate_date_histogram(request, code, module_name, environment)

    def aggregate_fields_filters(self, request, code, module_name, environment=None):
        return super().aggregate_fields_filters(request, code, module_name, environment)

    def _get_log_query_config_by_env(self, env: ModuleEnvironment, process_type: Optional[str] = None):
        log_type = self.log_type
        if log_type == LogType.INGRESS:
            log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).ingress
        elif log_type == LogType.STANDARD_OUTPUT:
            log_config = ProcessLogQueryConfig.objects.select_process_irrelevant(env).stdout
        else:
            try:
                log_config = ProcessLogQueryConfig.objects.get_by_process_type(process_type=process_type, env=env).json
            except ProcessLogQueryConfig.DoesNotExist:
                raise ValueError("structured log must provide `process_type` field")
        return log_config

    def _get_log_query_config(self, process_type: Optional[str] = None):
        module = self.get_module_via_path()
        stag = module.get_envs("stag")
        prod = module.get_envs("prod")
        # 初始化 env log 模型, 保证数据库对象存在且是 settings 中的最新配置
        setup_env_log_model(stag)
        setup_env_log_model(prod)
        stag_config = self._get_log_query_config_by_env(stag, process_type=process_type)
        prod_config = self._get_log_query_config_by_env(prod, process_type=process_type)
        if stag_config != prod_config:
            raise ValueError("`env` field must be specified for this module")
        return prod_config

    def _make_base_search(
        self,
        search_params: ElasticSearchParams,
        mappings: dict,
        time_range: SmartTimeRange,
        limit: int = DEFAULT_LOG_BATCH_SIZE,
        offset: int = 0,
    ) -> SmartSearch:
        module = self.get_module_via_path()
        # 需要根据 mappings 来确定字段查询条件是否需要加 keyword
        es_filter = ModuleFilter(module=module, search_params=search_params, mappings=mappings)
        search = SmartSearch(time_field=search_params.timeField, time_range=time_range)
        search = es_filter.filter_by_module(search)
        search = es_filter.filter_by_builtin_filters(search)
        search = es_filter.filter_by_builtin_excludes(search)
        return search.limit_offset(limit=limit, offset=offset)


class LegacyStdoutLogAPIView(LegacyLogAPIMixin, StdoutLogAPIView):
    ...


class LegacyStructuredLogAPIView(LegacyLogAPIMixin, StructuredLogAPIView):
    ...


class LegacyIngressLogAPIView(LegacyLogAPIMixin, IngressLogAPIView):
    ...


class SysStructuredLogAPIView(StructuredLogAPIView):
    permission_classes: List = []

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_logs(self, request, code, module_name, environment):
        return super().query_logs(request, code, module_name, environment)


class LegacySysStructuredLogAPIView(LegacyLogAPIMixin, SysStructuredLogAPIView):
    permission_classes: List = []

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def query_logs(self, request, code, module_name, environment=None):
        # TODO: 调整成以前的返回值格式
        return super().query_logs(request, code, module_name, environment)
