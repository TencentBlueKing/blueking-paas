# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from collections import defaultdict

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.application import (
    app_view_actions_perm,
    application_perm_class,
)
from paasng.infras.bkmonitorv3.client import make_bk_monitor_client
from paasng.infras.bkmonitorv3.exceptions import BkMonitorGatewayServiceError, BkMonitorSpaceDoesNotExist
from paasng.infras.bkmonitorv3.models import BKMonitorSpace
from paasng.infras.bkmonitorv3.params import QueryAlertsParams
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.monitoring.monitor.alert_rules.ascode.exceptions import AsCodeAPIError
from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.misc.monitoring.monitor.alert_rules.manager import alert_rule_manager_cls
from paasng.misc.monitoring.monitor.models import AppDashboard
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import UserApplicationFilter
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.platform.modules.models import Module
from paasng.utils.error_codes import error_codes

from .exceptions import BKMonitorNotSupportedError
from .models import AppAlertRule
from .serializers import (
    AlarmStrategySLZ,
    AlertListByUserSLZ,
    AlertRuleSLZ,
    AlertSLZ,
    AppDashboardSLZ,
    ListAlarmStrategiesSLZ,
    ListAlertRulesSLZ,
    ListAlertsSLZ,
    SupportedAlertSLZ,
)


class AlertRulesView(GenericViewSet, ApplicationCodeInPathMixin):
    queryset = AppAlertRule.objects.all()
    serializer_class = AlertRuleSLZ
    pagination_class = None

    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {
                "list": AppAction.VIEW_BASIC_INFO,
                "update": AppAction.EDIT_ALERT_POLICY,
                "init_alert_rules": AppAction.EDIT_ALERT_POLICY,
            },
            default_action=AppAction.VIEW_ALERT_RECORDS,
        ),
    ]

    @swagger_auto_schema(query_serializer=ListAlertRulesSLZ)
    def list(self, request, code, module_name):
        """查询告警规则列表"""
        serializer = ListAlertRulesSLZ(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        queryset = self.queryset.filter(application=self.get_application()).filter(
            Q(module=self.get_module_via_path()) | Q(module=None)
        )

        if run_env := validated_data.get("environment"):
            queryset = queryset.filter(environment=run_env)

        if alert_code := validated_data.get("alert_code"):
            queryset = queryset.filter(alert_code=alert_code)

        if keyword := validated_data.get("keyword"):
            queryset = queryset.filter(display_name__contains=keyword)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, code, id):
        """更新告警规则"""
        filter_kwargs = {"id": id, "application": self.get_application()}
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
            supported_alerts.append({"alert_code": alert_code, "display_name": alert_config["display_name"]})

        serializer = SupportedAlertSLZ(supported_alerts, many=True)
        return Response(serializer.data)

    def init_alert_rules(self, request, code):
        """初始化告警规则"""
        application = self.get_application()

        try:
            alert_rule_manager_cls(application).init_rules()
        except BKMonitorNotSupportedError as e:
            raise error_codes.INIT_ALERT_RULES_FAILED.f(str(e))
        except AsCodeAPIError:
            raise error_codes.INIT_ALERT_RULES_FAILED

        return Response()


class ListAlertsView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(request_body=ListAlertsSLZ, responses={200: AlertSLZ(many=True)})
    def list(self, request, code):
        """查询告警"""
        serializer = ListAlertsSLZ(data=request.data, context={"app_codes": [code]})
        serializer.is_valid(raise_exception=True)
        query_params: QueryAlertsParams = serializer.validated_data
        if not query_params.bk_biz_ids:
            # 应用的 BkMonitorSpace 不存在（应用未部署或配置监控）时，返回空列表
            return Response([])

        tenant_id = get_tenant_id_for_app(code)
        try:
            alerts = make_bk_monitor_client(tenant_id).query_alerts(query_params)
        except BkMonitorGatewayServiceError as e:
            raise error_codes.QUERY_ALERTS_FAILED.f(str(e))

        serializer = AlertSLZ(alerts, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=ListAlertsSLZ, responses={200: AlertListByUserSLZ()})
    def list_alerts_by_user(self, request):
        """查询用户各应用告警及数量"""
        app_codes = UserApplicationFilter(request.user).filter().values_list("code", flat=True)
        if not app_codes:
            return Response([])

        serializer = ListAlertsSLZ(data=request.data, context={"app_codes": app_codes})
        serializer.is_valid(raise_exception=True)
        query_params: QueryAlertsParams = serializer.validated_data
        if not query_params.bk_biz_ids:
            # 应用的 BkMonitorSpace 不存在（应用未部署或配置监控）时，返回空列表
            return Response([])

        # 查询用户下所有应用的告警信息，这里直接按当前用户获取租户信息
        tenant_id = get_tenant(request.user).id
        # 查询告警
        bk_monitor_client = make_bk_monitor_client(tenant_id)
        try:
            alerts = bk_monitor_client.query_alerts(query_params)
        except BkMonitorGatewayServiceError as e:
            raise error_codes.QUERY_ALERTS_FAILED.f(str(e))

        if not alerts:
            return Response([])

        # 告警按 bk_biz_id 归类
        biz_grouped_alerts = defaultdict(list)
        for alert in alerts:
            bk_biz_id = str(alert["bk_biz_id"])
            biz_grouped_alerts[bk_biz_id].append(alert)

        # 查询应用的监控空间, 生成 bk_biz_id 对应 application 的 dict
        monitor_spaces = bk_monitor_client.query_space_biz_id(app_codes=app_codes)
        bizid_app_map = {space["bk_biz_id"]: space["application"] for space in monitor_spaces}

        # 告警按应用归类
        app_alerts = [
            {"application": bizid_app_map[bizid], "alerts": alerts} for bizid, alerts in biz_grouped_alerts.items()
        ]

        serializer = AlertListByUserSLZ(app_alerts, many=True)
        return Response(serializer.data)


class ListAlarmStrategiesView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(query_serializer=ListAlarmStrategiesSLZ, responses={200: AlarmStrategySLZ})
    def list(self, request, code):
        """查询告警策略"""
        serializer = ListAlarmStrategiesSLZ(data=request.data, context={"app_code": code})
        serializer.is_valid(raise_exception=True)

        tenant_id = get_tenant_id_for_app(code)
        try:
            alarm_strategies = make_bk_monitor_client(tenant_id).query_alarm_strategies(serializer.validated_data)
        except BkMonitorSpaceDoesNotExist:
            # BkMonitorSpace 不存在（应用未部署）时，返回空字典
            return Response({})
        except BkMonitorGatewayServiceError as e:
            raise error_codes.QUERY_ALARM_STRATEGIES_FAILED.f(str(e))

        serializer = AlarmStrategySLZ(alarm_strategies)
        return Response(serializer.data)


class GetDashboardInfoView(ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def get_dashboard_url(self, request, code):
        """获取应用在蓝鲸监控仪表盘页面的地址"""
        app = self.get_application()

        try:
            bk_biz_id = BKMonitorSpace.objects.get(application=app).iam_resource_id
        except BKMonitorSpace.DoesNotExist:
            return Response({"dashboard_url": settings.BK_MONITORV3_URL})
        else:
            return Response({"dashboard_url": f"{settings.BK_MONITORV3_URL}/?bizId={bk_biz_id}#/grafana/home"})

    def list_builtin_dashboards(self, request, code):
        """查询应用已内置的仪表盘信息，没有 bk_biz_id 时不返回数据"""
        app = self.get_application()
        try:
            bk_biz_id = BKMonitorSpace.objects.get(application=app).iam_resource_id
        except BKMonitorSpace.DoesNotExist:
            return Response([])

        # 查询应用所有已经内置的仪表盘
        dashboards = AppDashboard.objects.filter(application=app).order_by("created")
        serializer = AppDashboardSLZ(dashboards, context={"bk_biz_id": bk_biz_id}, many=True)

        # app_languages 中出现过的语言对应的仪表盘排到前面
        app_languages = set(Module.objects.filter(application=app).values_list("language", flat=True))
        sorted_data = sorted(serializer.data, key=lambda d: (d["language"] not in app_languages))
        return Response(sorted_data)
