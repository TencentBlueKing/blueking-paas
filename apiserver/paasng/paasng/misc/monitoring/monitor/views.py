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
from typing import Text

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.bkmonitorv3.client import make_bk_monitor_client
from paasng.infras.bkmonitorv3.exceptions import BkMonitorGatewayServiceError
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.monitoring.monitor.alert_rules.ascode.exceptions import AsCodeAPIError
from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.misc.monitoring.monitor.alert_rules.manager import AlertRuleManager
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import UserApplicationFilter
from paasng.utils.error_codes import error_codes
from paasng.utils.views import permission_classes as perm_classes

from .exceptions import BKMonitorNotSupportedError
from .models import AppAlertRule
from .phalanx import Client
from .serializer import (
    AppSummaryResultSLZ,
    EventGenreListQuerySLZ,
    EventGenreListSLZ,
    EventRecordAppSummaryQuerySLZ,
    EventRecordDetailsSLZ,
    EventRecordListQuerySLZ,
    EventRecordListSLZ,
    EventRecordMetricsQuerySLZ,
    EventRecordMetricsResultSLZ,
)
from .serializers import (
    AlarmStrategySLZ,
    AlertRuleSLZ,
    AlertSLZ,
    ListAlarmStrategiesSLZ,
    ListAlertRulesSLZ,
    ListAlertsSLZ,
    SupportedAlertSLZ,
)


class EventRecordView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(responses={200: EventRecordListSLZ}, request_body=EventRecordListQuerySLZ, tags=["查询告警记录"])
    def query(self, request: Request, code: Text):
        request_slz = EventRecordListQuerySLZ(data=request.data, partial=True)
        request_slz.is_valid(True)

        client = Client()
        params = request_slz.validated_data
        labels = params.setdefault("labels", {})
        labels["app"] = code

        result = client.get_event_records(**params)
        if not result:
            raise Http404()

        slz = EventRecordListSLZ(result)

        return Response(slz.data)

    @swagger_auto_schema(
        responses={200: AppSummaryResultSLZ}, query_serializer=EventRecordAppSummaryQuerySLZ, tags=["个人应用告警统计"]
    )
    def app_summary(self, request: Request):
        request_slz = EventRecordAppSummaryQuerySLZ(data=request.query_params, partial=True)
        request_slz.is_valid(True)

        results = []
        applications = {i.code: i for i in UserApplicationFilter(request.user).filter(order_by=["name"])}

        # query only when applications is not empty
        if applications:
            client = Client()
            params = request_slz.validated_data
            labels = params.setdefault("labels", {})
            labels["app"] = list(applications.keys())

            records = client.get_grouped_records(groups=["app"], **params)
            if not records:
                raise Http404()

            for i in records.results:
                app = applications[i.labels["app"]]
                results.append({"summary": i, "app": app})

        slz = AppSummaryResultSLZ({"results": results})

        return Response(slz.data)


class EventRecordDetailsView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(responses={200: EventRecordDetailsSLZ}, tags=["查询告警记录详情"])
    def get(self, request: Request, code: Text, record: Text):
        client = Client()

        result = client.get_event_record_details(record, labels={"app": code})
        if not result:
            raise Http404()

        slz = EventRecordDetailsSLZ(result)

        return Response(slz.data)


class EventRecordMetricsView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(
        responses={200: EventRecordMetricsResultSLZ}, query_serializer=EventRecordMetricsQuerySLZ, tags=["查询告警记录指标趋势"]
    )
    def get(self, request: Request, code: Text, record: Text):
        request_slz = EventRecordMetricsQuerySLZ(data=request.query_params)
        request_slz.is_valid(True)

        client = Client()
        result = client.get_event_record_metrics(
            record,
            request_slz.validated_data["start"],
            request_slz.validated_data["end"],
            request_slz.validated_data["step"],
        )
        if not result:
            raise Http404()

        slz = EventRecordMetricsResultSLZ(result)

        return Response(slz.data)


class EventGenreView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_ALERT_RECORDS)]

    @swagger_auto_schema(responses={200: EventGenreListSLZ}, query_serializer=EventGenreListQuerySLZ, tags=["查询告警类型"])
    def list(self, request: Request, code: Text):
        request_slz = EventGenreListQuerySLZ(data=request.query_params, partial=True)
        request_slz.is_valid(True)

        client = Client()

        result = client.get_event_genre(**request_slz.validated_data)
        if not result:
            raise Http404()

        slz = EventGenreListSLZ(result)

        return Response(slz.data)


class AlertRulesView(GenericViewSet, ApplicationCodeInPathMixin):
    queryset = AppAlertRule.objects.all()
    serializer_class = AlertRuleSLZ
    pagination_class = None

    @swagger_auto_schema(query_serializer=ListAlertRulesSLZ)
    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def list(self, request, code, module_name):
        """查询告警规则列表"""
        serializer = ListAlertRulesSLZ(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        queryset = self.queryset.filter(application=self.get_application()).filter(
            Q(module=self.get_module_via_path()) | Q(module=None)
        )

        if run_env := validated_data.get('environment'):
            queryset = queryset.filter(environment=run_env)

        if alert_code := validated_data.get('alert_code'):
            queryset = queryset.filter(alert_code=alert_code)

        if keyword := validated_data.get('keyword'):
            queryset = queryset.filter(display_name__contains=keyword)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @perm_classes([application_perm_class(AppAction.EDIT_ALERT_POLICY)], policy='merge')
    def update(self, request, code, id):
        """更新告警规则"""
        filter_kwargs = {'id': id, 'application': self.get_application()}
        instance = get_object_or_404(self.queryset, **filter_kwargs)

        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={200: SupportedAlertSLZ(many=True)})
    def list_supported_alert_rules(self, request):
        """列举支持的告警规则"""
        supported_alerts = []

        for alert_code, alert_config in DEFAULT_RULE_CONFIGS.items():
            supported_alerts.append({'alert_code': alert_code, 'display_name': alert_config['display_name']})

        serializer = SupportedAlertSLZ(supported_alerts, many=True)
        return Response(serializer.data)

    @perm_classes([application_perm_class(AppAction.EDIT_ALERT_POLICY)], policy='merge')
    def init_alert_rules(self, request, code):
        """初始化告警规则"""
        application = self.get_application()

        try:
            AlertRuleManager(application).init_rules()
        except BKMonitorNotSupportedError as e:
            raise error_codes.INIT_ALERT_RULES_FAILED.f(str(e))
        except AsCodeAPIError:
            raise error_codes.INIT_ALERT_RULES_FAILED

        return Response()


class ListAlertsView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(query_serializer=ListAlertsSLZ, responses={200: AlertSLZ(many=True)})
    def list(self, request, code):
        """查询告警"""
        serializer = ListAlertsSLZ(data=request.data, context={'app_code': code})
        serializer.is_valid(raise_exception=True)

        try:
            alerts = make_bk_monitor_client().query_alerts(serializer.validated_data)
        except BkMonitorGatewayServiceError as e:
            raise error_codes.QUERY_ALERTS_FAILED.f(str(e))

        serializer = AlertSLZ(alerts, many=True)
        return Response(serializer.data)


class ListAlarmStrategiesView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(query_serializer=ListAlarmStrategiesSLZ, responses={200: AlarmStrategySLZ})
    def list(self, request, code):
        """查询告警策略"""
        serializer = ListAlarmStrategiesSLZ(data=request.data, context={'app_code': code})
        serializer.is_valid(raise_exception=True)

        try:
            alarm_strategies = make_bk_monitor_client().query_alarm_strategies(serializer.validated_data)
        except BkMonitorGatewayServiceError as e:
            raise error_codes.QUERY_ALARM_STRATEGIES_FAILED.f(str(e))

        serializer = AlarmStrategySLZ(alarm_strategies)
        return Response(serializer.data)
