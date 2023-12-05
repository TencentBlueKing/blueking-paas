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
from contextlib import contextmanager

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.paas_analysis import serializers as slzs
from paasng.accessories.paas_analysis.clients import SiteMetricsClient
from paasng.accessories.paas_analysis.constants import (
    MetricsDimensionType,
    MetricsInterval,
    MetricSourceType,
)
from paasng.accessories.paas_analysis.exceptions import PAClientException
from paasng.accessories.paas_analysis.services import (
    enable_ingress_tracking,
    get_ingress_tracking_status,
    get_or_create_custom_site_for_application,
    get_or_create_site_by_env,
)
from paasng.accessories.paas_analysis.utils import (
    get_metrics_source_type_from_str,
)
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


@contextmanager
def transform_client_exec():
    try:
        yield
    except PAClientException as e:
        logger.exception("an error occurred")
        raise error_codes.REQUEST_PA_FAIL from e
    except ImproperlyConfigured:
        logger.debug("paas-analysis is not configured")
        raise error_codes.REQUEST_PA_FAIL.f(_("paas-analysis service is not configured"))


############
# 访问量统计 #
############


class SiteGetterMixin(ApplicationCodeInPathMixin):
    def get_site_via_env(self):
        with transform_client_exec():
            return get_or_create_site_by_env(self.get_env_via_path())

    def get_custom_site(self, site_name: str):
        with transform_client_exec():
            return get_or_create_custom_site_for_application(self.get_application(), site_name=site_name)


class PageViewConfigViewSet(viewsets.ViewSet, SiteGetterMixin):
    """获取展示访问事件所需的基础配置"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_config(self, site):
        metric_source_type = self.kwargs.get("metric_source_type", "user_tracker")
        with transform_client_exec():
            client = SiteMetricsClient(site, get_metrics_source_type_from_str(metric_source_type))
            return client.get_site_pv_config()

    @swagger_auto_schema(tags=["访问量统计"], responses={200: slzs.PageViewConfigSLZ})
    def retrieve(self, request, code, module_name, environment, metric_source_type: str):
        site = self.get_site_via_env()
        return Response(data=self.get_config(site))

    @swagger_auto_schema(tags=["访问量统计"], responses={200: slzs.PageViewConfigSLZ})
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        return Response(data=self.get_config(site))


class PageViewMetricTrendViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定的`时间粒度`聚合查询某时间区间内的访问量数据"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_metric_trend(self, site):
        metric_source_type = self.kwargs.get("metric_source_type", "user_tracker")
        slz = slzs.IntervalMetricQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, get_metrics_source_type_from_str(metric_source_type))
            return client.get_metrics_aggregate_by_interval_about_site(
                MetricsInterval(params["interval"]),
                params["start_time"],
                params["end_time"],
                params["fill_missing_data"],
            )

    @swagger_auto_schema(
        query_serializer=slzs.IntervalMetricQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.PageViewMetricTrendSLZ},
    )
    def retrieve(self, request, code, module_name, environment, metric_source_type: str):
        site = self.get_site_via_env()
        metrics = self.get_metric_trend(site)
        return Response(data=metrics)

    @swagger_auto_schema(
        query_serializer=slzs.IntervalMetricQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.PageViewMetricTrendSLZ},
    )
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        metrics = self.get_metric_trend(site)
        return Response(data=metrics)


class PageViewTotalMetricsViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定的时间区间, 查询该范围内的总访问量"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_total_metrics(self, site):
        metric_source_type = self.kwargs.get("metric_source_type", "user_tracker")
        slz = slzs.AggregatedMetricsQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, get_metrics_source_type_from_str(metric_source_type))
            return client.get_total_page_view_metric_about_site(
                params["start_time"],
                params["end_time"],
            )

    @swagger_auto_schema(
        query_serializer=slzs.AggregatedMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.PageViewTotalMetricSLZ},
    )
    def retrieve(self, request, code, module_name, environment, metric_source_type: str):
        site = self.get_site_via_env()
        metric = self.get_total_metrics(site)
        return Response(data=metric)

    @swagger_auto_schema(
        query_serializer=slzs.AggregatedMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.PageViewTotalMetricSLZ},
    )
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        metric = self.get_total_metrics(site)
        return Response(data=metric)


class DimensionMetricsViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定的分组维度和时间区间, 查询该时间区间内, 按照分组维度聚合的数据"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_detail_via_dimension(self, site, dimension):
        metric_source_type = self.kwargs.get("metric_source_type", "user_tracker")
        slz = slzs.TableMetricsQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, get_metrics_source_type_from_str(metric_source_type))
            return client.get_metrics_dimension(
                MetricsDimensionType(dimension),
                params["start_time"],
                params["end_time"],
                params["limit"],
                params["offset"],
                params.get("ordering"),
                MetricsInterval(params["interval"]),
            )

    @swagger_auto_schema(
        query_serializer=slzs.TableMetricsQuerySLZ, tags=["访问量统计"], responses={200: slzs.MetricsDimensionSLZ}
    )
    def retrieve(self, request, code, module_name, environment, metric_source_type, dimension):
        site = self.get_site_via_env()
        metrics = self.get_detail_via_dimension(site, dimension)
        return Response(data=metrics)

    @swagger_auto_schema(
        query_serializer=slzs.TableMetricsQuerySLZ, tags=["访问量统计"], responses={200: slzs.MetricsDimensionSLZ}
    )
    def retrieve_for_custom_site(self, request, code, dimension, site_name):
        site = self.get_custom_site(site_name)
        metrics = self.get_detail_via_dimension(site, dimension)
        return Response(data=metrics)


############
# 自定义事件 #
############


class CustomEventConfigViewSet(viewsets.ViewSet, SiteGetterMixin):
    """获取展示自定义事件所需的基础配置"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_config(self, site):
        with transform_client_exec():
            client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
            return client.get_site_ce_config()

    @swagger_auto_schema(tags=["访问量统计"], responses={200: slzs.CustomEventConfigSLZ})
    def retrieve(self, request, code, module_name, environment):
        site = self.get_site_via_env()
        return Response(data=self.get_config(site))

    @swagger_auto_schema(tags=["访问量统计"], responses={200: slzs.CustomEventConfigSLZ})
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        return Response(data=self.get_config(site))


class CustomEventTotalMetricsViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定的时间区间, 查询该范围内的自定义事件总量"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_total_metrics(self, site):
        slz = slzs.AggregatedMetricsQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
            return client.get_total_custom_event_metric_about_site(
                params["start_time"],
                params["end_time"],
            )

    @swagger_auto_schema(
        query_serializer=slzs.AggregatedMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventTotalMetricSLZ},
    )
    def retrieve(self, request, code, module_name, environment):
        site = self.get_site_via_env()
        return Response(data=self.get_total_metrics(site))

    @swagger_auto_schema(
        query_serializer=slzs.AggregatedMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventTotalMetricSLZ},
    )
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        return Response(data=self.get_total_metrics(site))


class CustomEventOverviewViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定时间区间, 查询该时间区间内, 按事件类别聚合后的自定义事件触发情况(即自定义事件概览)"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_overview(self, site):
        slz = slzs.TableMetricsQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
            return client.get_custom_event_overview(
                params["start_time"],
                params["end_time"],
                params["limit"],
                params["offset"],
                params.get("ordering"),
                MetricsInterval(params["interval"]),
            )

    @swagger_auto_schema(
        query_serializer=slzs.TableMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventOverviewTableSLZ},
        operation_id="custom-event-overview",
    )
    def retrieve(self, request, code, module_name, environment):
        site = self.get_site_via_env()
        return Response(data=self.get_overview(site))

    @swagger_auto_schema(
        query_serializer=slzs.TableMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventOverviewTableSLZ},
        operation_id="custom-event-overview-for-custom-site",
    )
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        return Response(data=self.get_overview(site))


class CustomEventDetailViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定时间区间, 查询该时间区间内, 按事件类别过滤, 再按 事件id 和 维度 聚合后的事件触发情况(即自定义事件详情)"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_detail_via_category_and_dimension(self, site, category, dimension):
        slz = slzs.TableMetricsQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
            return client.get_custom_event_detail(
                category,
                MetricsDimensionType(dimension),
                params["start_time"],
                params["end_time"],
                params["limit"],
                params["offset"],
                params.get("ordering"),
                MetricsInterval(params["interval"]),
            )

    @swagger_auto_schema(
        query_serializer=slzs.TableMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventDetailTableSLZ},
        operation_id="custom-event-detail",
    )
    def retrieve(self, request, code, module_name, environment, category, dimension):
        site = self.get_site_via_env()
        return Response(data=self.get_detail_via_category_and_dimension(site, category, dimension))

    @swagger_auto_schema(
        query_serializer=slzs.TableMetricsQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventDetailTableSLZ},
        operation_id="custom-event-detail-for-custom-site",
    )
    def retrieve_for_custom_site(self, request, code, site_name, category, dimension):
        site = self.get_custom_site(site_name)
        return Response(data=self.get_detail_via_category_and_dimension(site, category, dimension))


class CustomEventTrendViewSet(viewsets.ViewSet, SiteGetterMixin):
    """根据指定的`时间粒度`聚合查询某时间区间内的自定义事件触发次数(即自定义事件触发趋势)"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_metric_trend(self, site):
        slz = slzs.IntervalMetricQuerySLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        with transform_client_exec():
            client = SiteMetricsClient(site, MetricSourceType.USER_TRACKER)
            return client.get_custom_event_trend_about_site(
                MetricsInterval(params["interval"]),
                params["start_time"],
                params["end_time"],
                params["fill_missing_data"],
            )

    @swagger_auto_schema(
        query_serializer=slzs.IntervalMetricQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventMetricTrendSLZ},
        operation_id="custom-event-trend",
    )
    def retrieve(self, request, code, module_name, environment):
        site = self.get_site_via_env()
        return Response(data=self.get_metric_trend(site))

    @swagger_auto_schema(
        query_serializer=slzs.IntervalMetricQuerySLZ,
        tags=["访问量统计"],
        responses={200: slzs.CustomEventMetricTrendSLZ},
        operation_id="custom-event-trend-for-custom-site",
    )
    def retrieve_for_custom_site(self, request, code, site_name):
        site = self.get_custom_site(site_name)
        return Response(data=self.get_metric_trend(site))


class IngressConfigViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """基于访问日志统计的配置管理"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(responses={200: slzs.IngressTrackingStatusSLZ}, tags=["访问量统计"])
    def get_tracking_status(self, request, code, module_name):
        """获取当前日志统计功能状态"""
        module = self.get_module_via_path()

        # Any environment is fine for status query, we will use the first returned environment
        env = module.envs.first()
        status = get_ingress_tracking_status(env)
        return Response({"status": status})

    @swagger_auto_schema(query_serializer=slzs.IngressTrackingStatusSLZ, tags=["访问量统计"])
    def update_tracking_status(self, request, code, module_name):
        """手动修改基于日志统计功能状态"""
        slz = slzs.IngressTrackingStatusSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        if not data["status"]:
            raise error_codes.ERROR_UPDATING_TRACKING_STATUS.f(_("暂不允许关闭日志统计功能"))

        module = self.get_module_via_path()
        for env in module.envs.all():
            with transform_client_exec():
                enable_ingress_tracking(env)

        return Response(data={})
