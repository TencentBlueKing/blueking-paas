# -*- coding: utf-8 -*-
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
import logging
from typing import List, Type

from django.conf import settings
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import ScanError
from pydantic import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_required
from paasng.metrics import LOG_SEARCH_COUNTER
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.log import serializers
from paasng.platform.log.client import LogClient, SmartTimeRange
from paasng.platform.log.constants import LogType
from paasng.platform.log.exceptions import UnknownEngineAppNameError
from paasng.platform.log.filters import AppAccessLogFilter, AppLogFilter, BaseAppFilter
from paasng.platform.log.models import IngressLogPage, LogPage, ResponseWrapper, SimpleDomainSpecialLanguage
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class LogBaseAPIView(APIView, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def get_extra_params_by_log_type(log_type: LogType) -> dict:
        if log_type == LogType.INGRESS:
            return dict(
                index_pattern=settings.ES_K8S_LOG_INDEX_NGINX_PATTERNS,
                log_page_class=IngressLogPage,
            )
        else:
            return dict(index_pattern=settings.ES_K8S_LOG_INDEX_PATTERNS, log_page_class=LogPage)

    def make_app_filter(self, log_type: LogType) -> BaseAppFilter:
        """根据查询的日志类型, 返回对应的应用信息过滤器"""

        application = self.get_application()
        module = self.get_module_via_path()
        region = application.region
        app_code = application.code

        if log_type == LogType.INGRESS:
            return AppAccessLogFilter(region=region, app_code=app_code, module_name=module.name)
        else:
            return AppLogFilter(region=region, app_code=app_code, module_name=module.name)

    def _gen_client(self, request, slz_class: Type[Serializer]):
        slz = slz_class(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        if request.data:
            try:
                query_conditions = SimpleDomainSpecialLanguage(**request.data)
            except ValidationError:
                logger.exception("error log query conditions")
                raise error_codes.QUERY_REQUEST_ERROR
        else:
            # MatchAll as fallback
            query_conditions = SimpleDomainSpecialLanguage(query={})

        log_type = LogType(params["log_type"])
        app_filter = self.make_app_filter(log_type)

        smart_time_range = SmartTimeRange(
            time_range=params["time_range"], start_time=params.get("start_time"), end_time=params.get("end_time")
        )
        try:
            client = LogClient(
                app_filter=app_filter,
                query_conditions=query_conditions,
                smart_time_range=smart_time_range,
                **self.get_extra_params_by_log_type(log_type=log_type)
            )
        except Exception as e:
            logger.exception(e)
            raise error_codes.QUERY_LOG_FAILED.f(_('日志查询失败，请稍后再试。'))
        return client, params


class LogTimeChartAPIView(LogBaseAPIView):
    def handle(self, request, code, module_name):
        """查询 [日志数量 x 时间] 直方图"""
        client, params = self._gen_client(request, serializers.AppLogQuerySLZ)
        # 过滤掉 stderr, stdout
        log_type = LogType(params["log_type"])
        if log_type == LogType.STRUCTURED:
            client.query_conditions.add_exclude_conditions(stream=["stderr", "stdout"])
        elif log_type == LogType.INGRESS:
            client.query_conditions.add_terms_conditions(stream=["stdout"])

        try:
            data = client.get_log_count_histogram()
        except RequestError:
            raise error_codes.QUERY_REQUEST_ERROR
        except Exception:
            logger.exception("failed to get count histogram")
            raise error_codes.QUERY_LOG_FAILED

        return Response(ResponseWrapper.parse_obj({"code": 0, "data": data}).dict())

    @swagger_auto_schema(
        query_serializer=serializers.AppLogQuerySLZ(),
        tags=["日志搜索"],
    )
    def get(self, request, code, module_name):
        return self.handle(request, code, module_name)

    @swagger_auto_schema(
        query_serializer=serializers.AppLogQuerySLZ(), tags=["日志搜索"], request_body=SimpleDomainSpecialLanguage
    )
    def post(self, request, code, module_name):
        return self.handle(request, code, module_name)


class LogFiltersAPIView(LogBaseAPIView):
    def handle(self, request, code, module_name):
        """获取日志筛选条件列表"""
        client, params = self._gen_client(request, serializers.AppLogQuerySLZ)
        try:
            log_type = LogType(params["log_type"])
            include_es_fields = False
            count_num = 200
            if log_type == LogType.STRUCTURED:
                # 过滤掉 stderr, stdout
                client.query_conditions.add_exclude_conditions(stream=["stderr", "stdout"])
                include_es_fields = True
            elif log_type == LogType.STANDARD_OUTPUT:
                # 仅查询 stderr, stdout
                client.query_conditions.add_terms_conditions(stream=["stderr", "stdout"])
            elif log_type == LogType.INGRESS:
                client.query_conditions.add_terms_conditions(stream=["stdout"])
                include_es_fields = True

            data = client.get_field_filters(include_es_fields=include_es_fields, count_num=count_num)
        except RequestError:
            raise error_codes.QUERY_REQUEST_ERROR
        except Exception:
            logger.exception("failed to get log")
            raise error_codes.QUERY_LOG_FAILED

        return Response(ResponseWrapper.parse_obj({"code": 0, "data": data}).dict())

    @swagger_auto_schema(
        query_serializer=serializers.AppLogQuerySLZ(),
        tags=["日志搜索"],
    )
    def get(self, request, code, module_name):
        return self.handle(request, code, module_name)

    @swagger_auto_schema(
        query_serializer=serializers.AppLogQuerySLZ(), tags=["日志搜索"], request_body=SimpleDomainSpecialLanguage
    )
    def post(self, request, code, module_name):
        return self.handle(request, code, module_name)


class StructuredLogAPIView(LogBaseAPIView):
    def handle(self, request, code, module_name):
        """
        获取「结构化」日志列表, 带分页
        """
        client, params = self._gen_client(request, serializers.AppLogListQuerySLZ)
        # 过滤掉 stderr, stdout
        client.query_conditions.add_exclude_conditions(stream=["stderr", "stdout"])
        page = params["page"]
        page_size = params["page_size"]

        try:
            data = client.query_logs(page, page_size)
        except RequestError:
            raise error_codes.QUERY_REQUEST_ERROR
        except Exception:
            logger.exception("failed to get logs")
            raise error_codes.QUERY_LOG_FAILED

        LOG_SEARCH_COUNTER.labels(
            environment=request.GET.get('environment', 'all'), stream=request.GET.get('stream', 'all')
        ).inc()

        if data is None:
            logger.error(
                "Can't not query log list from es for app: %s, module: %s",
                client.app_filter.app_code,
                client.app_filter.module_name,
            )
            raise error_codes.QUERY_REQUEST_ERROR
        return Response(ResponseWrapper(**{"code": 0, "data": data}).dict())

    @swagger_auto_schema(query_serializer=serializers.AppLogListQuerySLZ(), tags=["日志搜索"])
    def get(self, request, code, module_name):
        return self.handle(request, code, module_name)

    @swagger_auto_schema(
        query_serializer=serializers.AppLogListQuerySLZ(),
        tags=["日志搜索"],
        request_body=SimpleDomainSpecialLanguage,
    )
    def post(self, request, code, module_name):
        return self.handle(request, code, module_name)


class StandardOutputLogAPIView(LogBaseAPIView):
    def handle(self, request, code, module_name):
        """
        标准日志输出 API
        """
        client, params = self._gen_client(request, serializers.ESScrollSLZ)
        # 仅查询 stderr, stdout
        client.query_conditions.add_terms_conditions(stream=["stderr", "stdout"])

        scroll_id = params["scroll_id"]
        try:
            scroll = client.query_scrollable_logs(scroll_id)
        except ScanError as e:
            # 大概率是 scroll_id 失效
            logger.exception("scroll_id 失效, 日志查询失败")
            raise error_codes.QUERY_LOG_FAILED.f(_('日志查询快照失效, 请刷新后重试。')) from e
        except RequestError:
            logger.exception("query request error")
            raise error_codes.QUERY_REQUEST_ERROR
        except Exception:
            logger.exception("failed to get log")
            raise error_codes.QUERY_LOG_FAILED

        return Response(ResponseWrapper.parse_obj({"code": 0, "data": scroll}).dict())

    @swagger_auto_schema(query_serializer=serializers.ESScrollSLZ(), tags=["日志搜索"])
    def get(self, request, code, module_name):
        return self.handle(request, code, module_name)

    @swagger_auto_schema(
        query_serializer=serializers.ESScrollSLZ(),
        tags=["日志搜索"],
        request_body=SimpleDomainSpecialLanguage,
    )
    def post(self, request, code, module_name):
        return self.handle(request, code, module_name)


class IngressLogAPIView(LogBaseAPIView):
    """Ingress 接入层日志查询"""

    def handle(self, request, code, module_name):
        """
        获取「结构化」日志列表, 带分页
        """
        client, params = self._gen_client(request=request, slz_class=serializers.AppIngressListQuerySLZ)
        client.query_conditions.add_terms_conditions(stream=["stdout"])
        page = params["page"]
        page_size = params["page_size"]

        try:
            data = client.query_logs(page, page_size)
        except RequestError:
            raise error_codes.QUERY_REQUEST_ERROR
        except UnknownEngineAppNameError as e:
            raise error_codes.QUERY_REQUEST_ERROR.f(str(e))
        except Exception:
            logger.exception("failed to get log")
            raise error_codes.QUERY_LOG_FAILED

        LOG_SEARCH_COUNTER.labels(
            environment=request.GET.get('environment', 'all'), stream=request.GET.get('stream', 'all')
        ).inc()

        if data is None:
            logger.error(
                "Can't not query log list from es for app: %s, module: %s",
                client.app_filter.app_code,
                client.app_filter.module_name,
            )
            raise error_codes.QUERY_REQUEST_ERROR
        return Response(ResponseWrapper(**{"code": 0, "data": data}).dict())

    @swagger_auto_schema(query_serializer=serializers.AppLogListQuerySLZ(), tags=["日志搜索"])
    def get(self, request, code, module_name):
        return self.handle(request, code, module_name)

    @swagger_auto_schema(
        query_serializer=serializers.AppLogListQuerySLZ(),
        tags=["日志搜索"],
        request_body=SimpleDomainSpecialLanguage,
    )
    def post(self, request, code, module_name):
        return self.handle(request, code, module_name)


class SysStructuredLogAPIView(StructuredLogAPIView):
    permission_classes: List = []

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def get(self, request, code, module_name):
        return self.handle(request, code, module_name)

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def post(self, request, code, module_name):
        return self.handle(request, code, module_name)
