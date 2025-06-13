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

from typing import Dict, List

import rest_framework.request
import xlwt
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator, EnvClusterService
from paasng.accessories.publish.entrance.exposer import get_exposed_url
from paasng.core.core.storages.redisdb import DefaultRediStore
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.helpers import (
    add_role_members,
    fetch_application_members,
    fetch_role_members,
    fetch_user_roles,
    remove_user_all_roles,
)
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.application import (
    ApplicationDetailSLZ,
    ApplicationSLZ,
    AppOperationReportCollectionTaskOutputSLZ,
    AppOperationReportListInputSLZ,
    AppOperationReportOutputSLZ,
    BindEnvClusterSLZ,
)
from paasng.plat_admin.admin42.utils.filters import ApplicationFilterBackend
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.plat_admin.admin42.views.bk_plugins import is_plugin_instance_exist, is_user_plugin_admin
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationRole
from paasng.platform.applications.models import Application, ApplicationFeatureFlag
from paasng.platform.applications.serializers import ApplicationFeatureFlagSLZ, ApplicationMemberSLZ
from paasng.platform.applications.signals import application_member_updated
from paasng.platform.applications.tasks import cal_app_resource_quotas, sync_developers_to_sentry
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import AppOperationReport, AppOperationReportCollectionTask
from paasng.utils.error_codes import error_codes


class ApplicationListView(GenericTemplateView):
    """Application列表 的模板视图"""

    name = "应用列表"
    queryset = Application.objects.all()
    serializer_class = ApplicationSLZ
    template_name = "admin42/applications/list_applications.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    filter_backends = [ApplicationFilterBackend]

    def get_context_data(self, **kwargs):
        self.paginator.default_limit = 10
        if "view" not in kwargs:
            kwargs["view"] = self

        # 获取所有应用的资源使用总量
        store = DefaultRediStore(rkey="quotas::app")
        app_resource_quotas = store.get()
        # 未获取到，则在在后台计算
        if not app_resource_quotas:
            cal_app_resource_quotas.delay()
        else:
            # 以获取到所有应用的资源使用量，则按资源使用率排序分页
            return self.get_app_resource_context_data(app_resource_quotas, **kwargs)

        data = self.list(self.request, *self.args, **self.kwargs)
        kwargs["application_list"] = data
        kwargs["pagination"] = self.get_pagination_context(self.request)
        return kwargs

    # TODO Deprecated 应用资源配额 & 使用情况不在应用列表展示，另开独立页面
    def get_app_resource_context_data(self, app_resource_quotas, **kwargs):
        # 手动按资源的使用量排序分页
        offset = self.paginator.get_offset(self.request)
        limit = self.paginator.get_limit(self.request)
        queryset = self.filter_queryset(self.get_queryset())

        if self.request.query_params.get("search_term"):
            # 有查询参数则不按资源用量排序
            page = queryset[offset : offset + limit]
        else:
            # 应用资源排序后的信息
            page_app_code_list = list(app_resource_quotas.keys())[offset : offset + limit]
            page = queryset.filter(code__in=page_app_code_list)

        data = self.get_serializer(page, many=True, context={"app_resource_quotas": app_resource_quotas}).data

        def get_memory_for_desc_order(item):
            try:
                return int(item["resource_quotas"]["memory"])
            except (KeyError, ValueError):
                # 可能是 '--' 无效值
                return 0

        data = sorted(data, key=lambda item: get_memory_for_desc_order(item), reverse=True)
        kwargs["application_list"] = data

        # 没有调用默认的 paginate_queryset 方法，需要手动给 paginator 的参数赋值
        self.paginator.count = self.paginator.get_count(queryset)
        self.paginator.limit = limit
        self.paginator.offset = offset
        self.paginator.request = self.request
        kwargs["pagination"] = self.get_pagination_context(self.request)
        return kwargs


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
    template_name = "admin42/applications/list_evaluations.html"
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


class ApplicationDetailBaseView(GenericTemplateView):
    """Application详情概览页"""

    template_name = "admin42/applications/detail/base.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    # 描述当前高亮的导航栏
    name: str = ""

    def get_context_data(self, **kwargs):
        if "view" not in kwargs:
            kwargs["view"] = self

        application = self.get_application()
        kwargs["application"] = ApplicationDetailSLZ(application).data
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_application(self) -> Application:
        """Get the application object from the URL path."""
        code = self.kwargs["code"]
        return get_object_or_404(Application, code=code)


class ApplicationOverviewView(ApplicationDetailBaseView):
    """应用详情概览页"""

    queryset = Application.objects.all()
    serializer_class = ApplicationSLZ
    template_name = "admin42/applications/detail/overview.html"
    name = "概览"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        kwargs["USER_IS_ADMIN_IN_APP"] = self.request.user.username in fetch_role_members(
            application.code, ApplicationRole.ADMINISTRATOR
        )
        kwargs["ALLOW_CREATE_PLUGIN_AND_IS_PLUGIN_APP"] = application.is_plugin_app and is_plugin_instance_exist(
            self.kwargs["code"]
        )
        if kwargs["ALLOW_CREATE_PLUGIN_AND_IS_PLUGIN_APP"]:
            kwargs["USER_IS_ADMIN_IN_PLUGIN"] = is_user_plugin_admin(self.kwargs["code"], self.request.user.username)

        # 注：不同模块 / 环境可选的集群可能是不同的 -> {module_name-environment [available_clusters]}
        cluster_choices: Dict[str, List[Dict[str, str]]] = {}
        for env in application.envs.all():
            ctx = AllocationContext.from_module_env(env)
            ctx.username = self.request.user.username
            cluster_choices[f"{env.module.name}-{env.environment}"] = [
                {"id": cluster.name, "name": cluster.name} for cluster in ClusterAllocator(ctx).list()
            ]

        kwargs["cluster_choices"] = cluster_choices

        # Get the exposed URL for all environments
        env_urls: Dict[int, str] = {}
        for env in application.envs.all():
            if url_obj := get_exposed_url(env):
                env_urls[env.id] = url_obj.address

        kwargs["env_urls"] = env_urls

        return kwargs


class AppEnvConfManageView(viewsets.GenericViewSet):
    """应用部署环境配置管理"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def bind_cluster(self, request, code, module_name, environment):
        """切换环境所绑定的集群"""
        # Get the environment object
        application = get_object_or_404(Application, code=code)
        env = application.get_module(module_name).envs.get(environment=environment)

        slz = BindEnvClusterSLZ(data=request.data, context={"module_env": env, "operator": request.user.username})
        slz.is_valid(raise_exception=True)

        data_before = DataDetail(data=EnvClusterService(env=env).get_cluster_name())
        EnvClusterService(env=env).bind_cluster(cluster_name=slz.validated_data["cluster_name"])

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.BIND_CLUSTER,
            target=OperationTarget.APP,
            app_code=code,
            module_name=module_name,
            environment=environment,
            data_before=data_before,
            data_after=DataDetail(data=EnvClusterService(env=env).get_cluster_name()),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationMembersManageView(ApplicationDetailBaseView):
    """Application 应用成员管理页"""

    template_name = "admin42/applications/detail/base_info/members.html"
    name = "成员管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["ROLE_PERMISSION_SPEC"] = {
            ApplicationRole.ADMINISTRATOR.value: ["应用开发", "上线审核", "应用推广", "成员管理"],
            ApplicationRole.DEVELOPER.value: ["应用开发", "应用推广"],
            ApplicationRole.OPERATOR.value: ["上线审核", "应用推广"],
        }
        kwargs["PERMISSION_LIST"] = ["应用开发", "上线审核", "应用推广", "成员管理"]
        kwargs["ROLE_CHOICES"] = {
            key: value
            for value, key in ApplicationRole.get_django_choices()
            if value in kwargs["ROLE_PERMISSION_SPEC"]
        }

        return kwargs


class ApplicationMembersManageViewSet(viewsets.GenericViewSet):
    """Application应用成员 CRUD 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    @staticmethod
    def _gen_data_detail(code: str, username: str) -> DataDetail:
        return DataDetail(
            data={
                "username": username,
                "roles": [ApplicationRole(role).name.lower() for role in fetch_user_roles(code, username)],
            },
        )

    def list(self, request, *args, **kwargs):
        application = get_object_or_404(Application, code=kwargs["code"])
        members = fetch_application_members(application.code)
        return Response(ApplicationMemberSLZ(members, many=True).data)

    def destroy(self, request, code, username):
        application = get_object_or_404(Application, code=code)
        data_before = self._gen_data_detail(code, username)
        try:
            remove_user_all_roles(application.code, username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.DELETE_APP_MEMBERS_ERROR.f(e.message)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.APP_MEMBER,
            app_code=code,
            attribute="member",
            data_before=data_before,
            data_after=self._gen_data_detail(application.code, username),
        )

        self.sync_membership(application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, code):
        application = get_object_or_404(Application, code=code)
        username, role = request.data["username"], request.data["role"]
        data_before = self._gen_data_detail(application.code, username)

        try:
            remove_user_all_roles(application.code, username)
            add_role_members(application.code, ApplicationRole(role), username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.UPDATE_APP_MEMBERS_ERROR.f(e.message)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.APP_MEMBER,
            app_code=code,
            data_before=data_before,
            data_after=self._gen_data_detail(application.code, username),
        )

        self.sync_membership(application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def sync_membership(self, application):
        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)


class ApplicationFeatureFlagsView(ApplicationDetailBaseView):
    """Application应用特性管理页"""

    template_name = "admin42/applications/detail/base_info/app_feature_flags.html"
    name = "特性管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        application_features = ApplicationFeatureFlag.objects.get_application_features(application=application)
        kwargs["APP_FEATUREFLAG_CHOICES"] = dict(AppFeatureFlag.get_django_choices())
        kwargs["feature_flag_list"] = ApplicationFeatureFlagSLZ(
            [{"name": key, "effect": value} for key, value in application_features.items()], many=True
        ).data
        return kwargs


class ApplicationFeatureFlagsViewset(viewsets.GenericViewSet):
    """Application应用特性 CRUD 接口"""

    serializer_class = ApplicationFeatureFlagSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request, code):
        application = get_object_or_404(Application, code=code)
        application_features = ApplicationFeatureFlag.objects.get_application_features(application=application)
        return Response(
            ApplicationFeatureFlagSLZ(
                [{"name": key, "effect": value} for key, value in application_features.items()], many=True
            ).data
        )

    def update(self, request, code):
        application = get_object_or_404(Application, code=code)
        data_before = DataDetail(data=application.feature_flag.get_application_features())
        application.feature_flag.set_feature(request.data["name"], request.data["effect"])
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.FEATURE_FLAG,
            app_code=application.code,
            data_after=DataDetail(data=application.feature_flag.get_application_features()),
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
