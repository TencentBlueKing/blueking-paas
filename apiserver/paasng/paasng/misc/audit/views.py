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

from django.conf import settings
from django.db.models import Max
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.models import AppAuditRecord
from paasng.misc.audit.serializers import AppAuditRecordSLZ, QueryRecentOperatedApplications, RecordForRencentAppSLZ
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import UserApplicationFilter


class ApplicationAuditRecordViewSet(mixins.ListModelMixin, viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """
    应用的操作审计记录
    list: 单应用的操作记录
    - [测试地址](/api/bkapps/applications/awesome-app/audit/records/)
    - 接口返回的顺序为按操作时间逆序
    - 返回记录条数通过limit设置，默认值5
    """

    serializer_class = AppAuditRecordSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]
    queryset = AppAuditRecord.objects.all()

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
        app_code_list = list(applications.values_list("code", flat=True))

        # 相关应用的所有操作记录
        user_app_record_queryset = AppAuditRecord.objects.filter(app_code__in=app_code_list)
        # 获取每个 app_code 的最新记录的 ID
        latest_ids = (
            user_app_record_queryset.values("app_code")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )
        latest_records = AppAuditRecord.objects.filter(id__in=latest_ids).order_by("-created")
        return latest_records

    def get(self, request, *args, **kwargs):
        serializer = QueryRecentOperatedApplications(data=request.GET)
        serializer.is_valid(raise_exception=True)

        records_queryset = self.get_queryset(serializer.data["limit"])
        return Response(RecordForRencentAppSLZ(records_queryset, many=True).data)
