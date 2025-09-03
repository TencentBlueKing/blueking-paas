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

from typing import List

import rest_framework.request
import xlwt
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.application import (
    AppOperationReportCollectionTaskOutputSLZ,
    AppOperationReportListInputSLZ,
    AppOperationReportOutputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import AppOperationReport, AppOperationReportCollectionTask


class ApplicationOperationReportMixin:
    request: rest_framework.request.Request

    def get_queryset(self):
        slz = AppOperationReportListInputSLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        queryset = AppOperationReport.objects.all()
        if search_term := params.get("search_term"):
            queryset = queryset.filter(Q(app__code__icontains=search_term) | Q(app__name__icontains=search_term))

        if issue_type := params.get("issue_type"):
            queryset = queryset.filter(issue_type=issue_type)

        if order_by := params.get("order_by"):
            queryset = queryset.order_by(order_by)

        return queryset


class ApplicationOperationEvaluationView(ApplicationOperationReportMixin, GenericTemplateView):
    name = "应用运营评估"
    template_name = "admin42/operation/list_evaluations.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        self.paginator.default_limit = 10

        kwargs = super().get_context_data(**kwargs)

        kwargs["latest_collect_task"] = None
        # 获取最近一次同步任务
        if latest_collect_task := AppOperationReportCollectionTask.objects.order_by("-start_at").first():
            kwargs["latest_collect_task"] = AppOperationReportCollectionTaskOutputSLZ(latest_collect_task).data

        kwargs["usage_report_list"] = AppOperationReportOutputSLZ(
            self.paginate_queryset(self.get_queryset()), many=True
        ).data
        kwargs["pagination"] = self.get_pagination_context(self.request)
        return kwargs


class ApplicationOperationReportExportView(ApplicationOperationReportMixin, viewsets.GenericViewSet):
    """导出应用运营报告"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def export(self, request, *args, **kwargs):
        work_book = xlwt.Workbook(encoding="utf-8")
        work_sheet = work_book.add_sheet("reports")

        # 表头
        sheet_headers = self.get_sheet_headers()
        for idx, value in enumerate(sheet_headers):
            work_sheet.col(idx).width = 256 * 20
            work_sheet.write(0, idx, value)

        # 数据
        sheet_data = self.get_sheet_data()
        for row_num, values in enumerate(sheet_data, start=1):
            for col_num, val in enumerate(values):
                work_sheet.write(row_num, col_num, val)

        response = HttpResponse(content_type="application/ms-excel")
        response["Content-Disposition"] = "attachment;filename=bk_paas3_application_operation_report.xls"
        work_book.save(response)
        return response

    def get_sheet_headers(self) -> List[str]:
        return [
            "应用 Code",
            "应用名称",
            "内存 Requests",
            "内存 Limits",
            "内存使用率（7d）",
            "CPU Requests",
            "CPU Limits",
            "CPU 使用率（7d）",
            "PV（30d）",
            "UV（30d）",
            "最新操作人",
            "最新操作时间",
            "问题类型",
            "问题描述",
            "应用管理员",
        ]

    def get_sheet_data(self) -> List[List[str]]:
        rows = []
        for rp in self.get_queryset():
            try:
                administrators = ", ".join(rp.app.get_administrators())
            except Exception:
                administrators = "--"

            rows.append(
                [
                    rp.app.code,
                    rp.app.name,
                    f"{round(rp.mem_requests / 1024, 2)} G",
                    f"{round(rp.mem_limits / 1024, 2)} G",
                    f"{round(rp.mem_usage_avg * 100, 2)}%",
                    f"{round(rp.cpu_requests / 1000, 2)} 核",
                    f"{round(rp.cpu_limits / 1000, 2)} 核",
                    f"{round(rp.cpu_usage_avg * 100, 2)}%",
                    str(rp.pv),
                    str(rp.uv),
                    rp.latest_operator if rp.latest_operator else "--",
                    rp.latest_operated_at.strftime("%Y-%m-%d %H:%M:%S") if rp.latest_operated_at else "--",
                    str(OperationIssueType.get_choice_label(rp.issue_type)),
                    ", ".join(rp.evaluate_result["issues"]) if rp.evaluate_result else "--",
                    administrators,
                ]
            )

        return rows
