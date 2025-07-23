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

import arrow
import xlwt
from django.db.models import Count, F
from django.http import HttpResponse
from django.views.generic import TemplateView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.statistics import (
    AppDeploymentFilterSlz,
    AppDeploymentSlz,
    DeveloperDeploymentSlz,
)
from paasng.platform.engine.models.deployment import Deployment
from paasng.utils.basic import get_username_by_bkpaas_user_id


class DeployStatisticsView(TemplateView, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.OPERATE_PLATFORM)]

    def get_context_data(self, **kwargs):
        kwargs.update(self.request.query_params)
        if "view" not in kwargs:
            kwargs["view"] = self
        kwargs["months"] = self.get_months()
        # DRF 中 GenericViewSet 再 as_view 时会将 name 属性重置为 None
        # 这里将直接传递上下文变量 name
        kwargs["view_name"] = "应用统计"

        kwargs["data_list"] = self.serializer_class(self.get_data(), many=True).data
        return kwargs

    def get_months(self):
        # 计算查询范围内的月份
        time_range = arrow.Arrow.span_range("month", self.query_params["start_time"], self.query_params["end_time"])
        months = [f"{t[0].year}-{t[0].month}" for t in time_range]
        return months

    def filter_queryset(self, qs):
        # 按时间过滤
        queryset = self.queryset.filter(
            created__gte=self.query_params["start_time"], created__lte=self.query_params["end_time"]
        )
        # 按部署环境过滤
        if self.query_params.get("only_prod"):
            queryset = queryset.filter(app_environment__environment="prod")

        return queryset

    def get(self, request, *args, **kwargs):
        query_slz = AppDeploymentFilterSlz(data=request.query_params)
        query_slz.is_valid(raise_exception=True)
        self.query_params = query_slz.validated_data
        return super().get(request, *args, **kwargs)

    def export(self, request, *args, **kwargs):
        query_slz = AppDeploymentFilterSlz(data=request.query_params)
        query_slz.is_valid(raise_exception=True)
        self.query_params = query_slz.validated_data

        # 构造xls
        work_book = xlwt.Workbook(encoding="utf-8")
        work_sheet = work_book.add_sheet("sheet1")

        # 表头
        sheet_headers = self.get_sheet_headers()
        for index, value in enumerate(sheet_headers):
            work_sheet.col(index).width = 256 * 20
            work_sheet.write(0, index, value)

        sheet_data = self.get_sheet_data()
        for row, data_list in enumerate(sheet_data):
            for i, data in enumerate(data_list):
                work_sheet.write(row + 1, i, data)

        xls_name = f"bk_paas3_{self.export_suffix}.xls"
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        response["Content-Disposition"] = f"attachment; filename={xls_name}"
        work_book.save(response)
        return response


class AppDeployStatisticsView(DeployStatisticsView):
    # 应用部署统计, 使用 "应用统计" 为了前端导航高亮
    name = "应用统计"
    export_suffix = "statistics_deploy_apps"
    template_name = "admin42/operation/statistics/statistics_deploy_apps.html"
    queryset = Deployment.objects.all()
    serializer_class = AppDeploymentSlz

    def get_data(self) -> list:
        queryset = self.filter_queryset(self.get_queryset())

        # 统计应用总的部署次数
        deployments = (
            queryset.values(
                code=F("app_environment__module__application__code"),
                name=F("app_environment__module__application__name"),
            )
            .annotate(total=Count("id"))
            .order_by("-total")
        )

        # 按月统计应用的部署次数
        # 线上数据库的的设置，不能直接使用 ExtractYear/ExtractMonth
        # https://stackoverflow.com/questions/45681227/extractyear-and-extractmonth-returning-none-in-django
        monthly_statistics = (
            queryset.extra(
                {
                    "year": "EXTRACT(YEAR from engine_deployment.created)",
                    "month": "EXTRACT(MONTH from engine_deployment.created)",
                }
            )
            .values("year", "month", code=F("app_environment__module__application__code"))
            .order_by("year", "month")
            .annotate(count=Count("id"))
        )
        for deployment in deployments:
            code = deployment["code"]

            # 最近操作人（最近一次部署）
            last_operator = (
                Deployment.objects.filter(app_environment__module__application__code=code)
                .order_by("-created")
                .first()
                .operator
            )
            deployment["last_operator"] = get_username_by_bkpaas_user_id(last_operator)

            # 按月统计部署次数
            monthly_data = monthly_statistics.filter(code=code)
            deployment["monthly_data_dict"] = {f"{m['year']}-{m['month']}": m["count"] for m in monthly_data}

            # 页面上先简单把所有月份的部署次数通过字符串渲染出来
            monthly_data_list = [f"{m['year']}-{m['month']}:{m['count']}" for m in monthly_data]
            deployment["monthly_summary"] = "; ".join(monthly_data_list)
        return deployments

    def get_sheet_headers(self) -> list:
        sheet_headers = ["应用ID", "应用名称", "最近操作人", "总的部署次数"]
        sheet_headers.extend(self.get_months())
        return sheet_headers

    def get_sheet_data(self) -> list:
        sheet_data = []

        months = self.get_months()
        data_list = self.get_data()
        for data in data_list:
            row = [data["code"], data["name"], data["last_operator"], data["total"]]
            for month in months:
                row.append(data["monthly_data_dict"].get(month, 0))
            sheet_data.append(row)
        return sheet_data


class DevelopersDeployStatisticsView(DeployStatisticsView):
    # 开发者部署统计, 使用 "应用统计" 为了前端导航高亮
    name = "应用统计"
    export_suffix = "statistics_deploy_developers"
    template_name = "admin42/operation/statistics/statistics_deploy_developers.html"
    queryset = Deployment.objects.all()
    serializer_class = DeveloperDeploymentSlz

    def get_data(self) -> list:
        queryset = self.filter_queryset(self.get_queryset())

        # 统计应用总的部署次数
        deployments = queryset.values("operator").annotate(total=Count("id")).order_by("-total")

        monthly_statistics = (
            queryset.extra(
                {
                    "year": "EXTRACT(YEAR from engine_deployment.created)",
                    "month": "EXTRACT(MONTH from engine_deployment.created)",
                }
            )
            .values("year", "month", "operator")
            .order_by("year", "month")
            .annotate(count=Count("id"))
        )
        for deployment in deployments:
            operator = deployment["operator"]
            deployment["developer"] = get_username_by_bkpaas_user_id(operator)

            # 按月统计部署次数
            monthly_data = monthly_statistics.filter(operator=operator)
            deployment["monthly_data_dict"] = {f"{m['year']}-{m['month']}": m["count"] for m in monthly_data}

            monthly_data_list = [f"{m['year']}-{m['month']}:{m['count']}" for m in monthly_data]
            deployment["monthly_summary"] = "; ".join(monthly_data_list)
        return deployments

    def get_sheet_headers(self) -> list:
        sheet_headers = ["开发者", "总的部署次数"]
        try:
            from paasng.plat_admin.admin42.utils.organization import UserOrganization

            sheet_headers.extend(UserOrganization.__annotations__.keys())
        except ImportError:
            pass

        sheet_headers.extend(self.get_months())
        return sheet_headers

    def get_sheet_data(self) -> list:
        sheet_data = []

        months = self.get_months()
        data_list = self.get_data()
        for data in data_list:
            row = [data["developer"], data["total"]]

            try:
                from paasng.plat_admin.admin42.utils.organization import get_user_organization

                organization = get_user_organization(data["developer"])
                row.extend(organization.__dict__.values())
            except ImportError:
                pass

            for month in months:
                row.append(data["monthly_data_dict"].get(month, 0))
            sheet_data.append(row)
        return sheet_data
