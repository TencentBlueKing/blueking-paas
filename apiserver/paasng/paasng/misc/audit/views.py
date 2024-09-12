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
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.models import AppLatestOperationRecord, AppOperationRecord
from paasng.misc.audit.serializers import (
    AppOperationRecordFilterSlZ,
    AppOperationRecordSLZ,
    QueryRecentOperationsSLZ,
    RecordForRecentAppSLZ,
)
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import UserApplicationFilter


class ApplicationAuditRecordViewSet(mixins.ListModelMixin, viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """
    应用的操作审计记录
    list: 单应用的操作记录
    - 接口返回的顺序为按操作时间逆序
    - 返回记录条数通过limit设置，默认值5
    """

    serializer_class = AppOperationRecordSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]
    queryset = AppOperationRecord.objects.all()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        slz = AppOperationRecordFilterSlZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        query_params = slz.validated_data

        if target := query_params.get("target"):
            queryset = queryset.filter(target=target)
        if operation := query_params.get("operation"):
            queryset = queryset.filter(operation=operation)
        if access_type := query_params.get("access_type"):
            queryset = queryset.filter(access_type=access_type)
        if result_code := query_params.get("result_code"):
            queryset = queryset.filter(result_code=result_code)
        if module_name := query_params.get("module_name"):
            queryset = queryset.filter(module_name=module_name)
        if environment := query_params.get("environment"):
            queryset = queryset.filter(environment=environment)
        if start_time := query_params.get("start_time"):
            queryset = queryset.filter(created__gte=start_time)
        if end_time := query_params.get("end_time"):
            queryset = queryset.filter(created__lte=end_time)
        if operator := query_params.get("operator"):
            operator = user_id_encoder.encode(settings.USER_TYPE, operator)
            queryset = queryset.filter(user=operator)
        return queryset

    @swagger_auto_schema(tags=["操作记录"], query_serializer=AppOperationRecordFilterSlZ)
    def list(self, request, *args, **kwargs):
        application = self.get_application()
        self.queryset = self.queryset.filter(app_code=application.code).order_by("-created")
        return super().list(request, *args, **kwargs)


class LatestApplicationsViewSet(APIView):
    """
    最近操作的应用列表
    get: 最近操作的应用列表
    - [测试地址](/api/bkapps/applications/lists/latest/)
    - 已经按照application去重
    - 接口返回的顺序为按操作时间逆序
    - 如果需要调整返回的应用数，通过limit参数指定（后台限制最大10个）, 如http://paas.bking.com/api/bkapps/applications/latest/?limit=5
    """

    def get_queryset(self, limit: int):
        applications = UserApplicationFilter(self.request.user).filter()
        # 可设置在应用列表中不展示插件应用
        if not settings.DISPLAY_BK_PLUGIN_APPS:
            applications = applications.exclude(is_plugin_app=True)
        application_ids = list(applications.values_list("id", flat=True))

        latest_operated_objs = (
            AppLatestOperationRecord.objects.filter(application__id__in=application_ids)
            .select_related("operation")
            .order_by("-latest_operated_at")[:limit]
        )
        # 每个应用的最近操作记录
        latest_records = [obj.operation for obj in latest_operated_objs]
        return latest_records

    def get(self, request, *args, **kwargs):
        serializer = QueryRecentOperationsSLZ(data=request.GET)
        serializer.is_valid(raise_exception=True)

        records_queryset = self.get_queryset(serializer.data["limit"])
        data = {"results": RecordForRecentAppSLZ(records_queryset, many=True).data}
        return Response(data)
