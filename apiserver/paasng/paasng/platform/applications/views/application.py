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

import logging
from typing import Dict, List, Set, Tuple

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.cnative.specs.resource import delete_bkapp, delete_networking
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paasng.accessories.publish.entrance.exposer import get_exposed_links
from paasng.accessories.publish.market.models import ApplicationExtraInfo, MarketConfig, Product
from paasng.infras.accounts.constants import FunctionType
from paasng.infras.accounts.models import make_verifier
from paasng.infras.accounts.permissions.application import (
    app_view_actions_perm,
    application_perm_class,
)
from paasng.infras.accounts.serializers import VerificationCodeSLZ
from paasng.infras.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError
from paasng.infras.bkmonitorv3.shim import update_or_create_bk_monitor_space
from paasng.infras.iam.helpers import fetch_user_main_role
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import add_app_audit_record
from paasng.platform.applications import serializers as slzs
from paasng.platform.applications.cleaner import ApplicationCleaner, delete_all_modules
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application, UserApplicationFilter, UserMarkedApplication
from paasng.platform.applications.pagination import ApplicationListPagination
from paasng.platform.applications.protections import AppResProtector, ProtectedRes, raise_if_protected
from paasng.platform.applications.utils import get_app_overview
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import (
    AppOperationReport,
    AppOperationReportCollectionTask,
    IdleAppNotificationMuteRule,
)
from paasng.platform.mgrlegacy.migrate import get_migration_process_status
from paasng.platform.modules.protections import ModuleDeletionPreparer
from paasng.utils import dictx
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ApplicationListViewSet(viewsets.ViewSet):
    """View class for application lists."""

    @swagger_auto_schema(query_serializer=slzs.ApplicationListDetailedSLZ())
    def list_detailed(self, request):
        """[API] 查询应用列表详情"""
        # get marked application ids
        marked_applications = UserMarkedApplication.objects.filter(owner=request.user.pk)
        marked_application_ids = set(marked_applications.values_list("application__id", flat=True))

        serializer = slzs.ApplicationListDetailedSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        # Get applications by given params
        applications = UserApplicationFilter(request.user).filter(
            include_inactive=params["include_inactive"],
            languages=params.get("language"),
            regions=params.get("region"),
            search_term=params.get("search_term"),
            source_origin=params.get("source_origin"),
            type_=params.get("type"),
            # 已下架的应用默认展示在最末尾
            order_by=["-is_active", params.get("order_by")],
            app_tenant_mode=params.get("app_tenant_mode"),
        )

        # 插件开发者中心正式上线前需要根据配置来决定应用列表中是否展示插件应用
        if not settings.DISPLAY_BK_PLUGIN_APPS:
            applications = applications.filter(is_plugin_app=False)

        # 查询我创建的应用时，也需要返回总的应用数量给前端
        all_app_count = applications.count()
        # 仅查询我创建的应用
        if params.get("exclude_collaborated") is True:
            applications = applications.filter(owner=request.user.pk)

        paginator = ApplicationListPagination()
        # 如果将用户标记的应用排在前面，需要特殊处理一下
        if params.get("prefer_marked"):
            applications_ids = applications.values_list("id", flat=True)
            applications_ids = sorted(applications_ids, key=lambda x: x in marked_application_ids, reverse=True)

            page = paginator.paginate_queryset(applications_ids, self.request, view=self)
            page_applications = list(Application.objects.filter(id__in=page).select_related("product"))
            page_applications = sorted(page_applications, key=lambda x: applications_ids.index(x.id))
        else:
            page_applications = paginator.paginate_queryset(applications, self.request, view=self)

        # Set exposed links property, to be used by the serializer later
        for app in page_applications:
            app._deploy_info = get_exposed_links(app)
        data = [
            {
                "application": application,
                "product": application.product if hasattr(application, "product") else None,
                "marked": application.id in marked_application_ids,
                # 应用市场访问地址信息
                "market_config": MarketConfig.objects.get_or_create_by_app(application)[0],
                "migration_status": get_migration_process_status(application),
            }
            for application in page_applications
        ]

        # 统计普通应用、云原生应用、外链应用的数量
        default_app_count = applications.filter(type=ApplicationType.DEFAULT).count()
        engineless_app_count = applications.filter(type=ApplicationType.ENGINELESS_APP).count()
        cloud_native_app_count = applications.filter(type=ApplicationType.CLOUD_NATIVE).count()
        # 统计我创建的应用数量
        my_app_count = applications.filter(owner=request.user.pk).count()

        serializer = slzs.ApplicationWithMarketSLZ(data, many=True)
        return paginator.get_paginated_response(
            serializer.data,
            extra_data={
                "default_app_count": default_app_count,
                "engineless_app_count": engineless_app_count,
                "cloud_native_app_count": cloud_native_app_count,
                "my_app_count": my_app_count,
                "all_app_count": all_app_count,
            },
        )

    @swagger_auto_schema(query_serializer=slzs.ApplicationListMinimalSLZ())
    def list_minimal(self, request):
        """[API] 查询简单应用列表"""
        # Get applications by given params
        serializer = slzs.ApplicationListMinimalSLZ(data=request.query_params)
        serializer.is_valid()
        params = serializer.data

        applications = UserApplicationFilter(request.user).filter(
            order_by=["name"],
            include_inactive=params["include_inactive"],
            source_origin=params.get("source_origin", None),
        )

        # 插件开发者中心正式上线前需要根据配置来决定应用列表中是否展示插件应用
        if not settings.DISPLAY_BK_PLUGIN_APPS:
            applications = applications.filter(is_plugin_app=False)

        # 目前应用在市场的 name 和 Application 中的 name 一致
        results = [{"application": application, "product": {"name": application.name}} for application in applications]
        serializer = slzs.ApplicationWithMarketMinimalSLZ(results, many=True)
        return Response({"count": len(results), "results": serializer.data})

    @swagger_auto_schema(query_serializer=slzs.SearchApplicationSLZ())
    def list_search(self, request):
        """
        App 搜索
        """
        serializer = slzs.SearchApplicationSLZ(data=request.query_params)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # if keyword do not match regex, then return none
            return Response({"count": 0, "results": []})

        params = serializer.data
        keyword = params.get("keyword")
        # Get applications which contains keywords
        applications = UserApplicationFilter(request.user).filter(
            include_inactive=params["include_inactive"], order_by=["name"], search_term=keyword
        )

        # get marked application ids
        marked_applications = UserMarkedApplication.objects.filter(owner=request.user.pk)
        marked_application_ids = set(marked_applications.values_list("application__id", flat=True))

        if params.get("prefer_marked"):
            # then sort it
            applications = sorted(applications, key=lambda app: app.id in marked_application_ids, reverse=True)

        data = [
            {
                "application": application,
                "marked": application.id in marked_application_ids,
            }
            for application in applications
        ]
        serializer = slzs.ApplicationWithMarkMinimalSLZ(data, many=True)
        return Response({"count": len(applications), "results": serializer.data})

    @swagger_auto_schema(
        tags=["应用列表"],
        operation_description="获取闲置的应用列表",
        responses={200: slzs.IdleApplicationListOutputSLZ()},
    )
    def list_idle(self, request):
        """获取闲置的应用列表"""
        app_codes = UserApplicationFilter(request.user).filter(order_by=["name"]).values_list("code", flat=True)

        latest_collected_at = None
        if collect_task := AppOperationReportCollectionTask.objects.order_by("-start_at").first():
            latest_collected_at = collect_task.start_at

        mute_rules = {
            (r.app_code, r.module_name, r.environment)
            for r in IdleAppNotificationMuteRule.objects.filter(user=request.user, expired_at__gt=timezone.now())
        }

        applications = []
        for report in AppOperationReport.objects.filter(
            app__code__in=app_codes, issue_type=OperationIssueType.IDLE
        ).select_related("app"):
            idle_module_envs = self._list_idle_module_envs(report, mute_rules)
            if not idle_module_envs:
                continue

            applications.append(
                {
                    "code": report.app.code,
                    "name": report.app.name,
                    "type": report.app.type,
                    "is_plugin_app": report.app.is_plugin_app,
                    "logo_url": report.app.get_logo_url(),
                    "administrators": report.administrators,
                    "developers": report.developers,
                    "module_envs": idle_module_envs,
                }
            )

        resp_data = {"collected_at": latest_collected_at, "applications": applications}
        return Response(data=slzs.IdleApplicationListOutputSLZ(resp_data).data)

    @staticmethod
    def _list_idle_module_envs(report: AppOperationReport, mute_rules: Set[Tuple[str, str, str]]) -> List[Dict]:
        idle_module_envs = []

        for module_name, mod_evaluate_result in report.evaluate_result["modules"].items():
            for env_name, env_evaluate_result in mod_evaluate_result["envs"].items():
                if env_evaluate_result["issue_type"] != OperationIssueType.IDLE:
                    continue
                # 有未过期的屏蔽规则的跳过
                if (report.app.code, module_name, env_name) in mute_rules:
                    continue

                path = f"modules.{module_name}.envs.{env_name}"
                env_res_summary = dictx.get_items(report.res_summary, path)
                env_deploy_summary = dictx.get_items(report.deploy_summary, path)
                idle_module_envs.append(
                    {
                        "module_name": module_name,
                        "env_name": env_name,
                        "cpu_quota": env_res_summary["cpu_limits"],
                        "memory_quota": env_res_summary["mem_limits"],
                        "cpu_usage_avg": env_res_summary["cpu_usage_avg"],
                        "latest_deployed_at": env_deploy_summary["latest_deployed_at"],
                    }
                )

        return slzs.IdleModuleEnvSLZ(idle_module_envs, many=True).data

    @swagger_auto_schema(
        tags=["应用列表"],
        operation_description="获取应用评估详情列表",
        query_serializer=slzs.ApplicationEvaluationListQuerySLZ(),
        responses={200: slzs.ApplicationEvaluationListResultSLZ()},
    )
    def list_evaluation(self, request):
        """获取应用评估详情列表"""
        slz = slzs.ApplicationEvaluationListQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        params = slz.validated_data

        latest_collected_at = None
        if collect_task := AppOperationReportCollectionTask.objects.order_by("-start_at").first():
            latest_collected_at = collect_task.start_at

        app_codes = UserApplicationFilter(request.user).filter().values_list("code", flat=True)

        reports = (
            AppOperationReport.objects.filter(
                app__code__in=app_codes,
            )
            .order_by(params["order"])
            .select_related("app")
        )

        if issue_type := params.get("issue_type"):
            reports = reports.filter(issue_type=issue_type)

        paginator = LimitOffsetPagination()
        paginated_reports = paginator.paginate_queryset(reports, request)

        applications = slzs.ApplicationEvaluationSLZ(paginated_reports, many=True).data
        return paginator.get_paginated_response(
            {
                "collected_at": latest_collected_at,
                "applications": applications,
            }
        )

    @swagger_auto_schema(
        tags=["应用列表"],
        operation_description="获取应用评估各状态数量",
        responses={200: slzs.ApplicationEvaluationIssueCountListResultSLZ()},
    )
    def list_evaluation_issue_count(self, request):
        """获取应用评估各状态数量"""
        latest_collected_at = None
        if collect_task := AppOperationReportCollectionTask.objects.order_by("-start_at").first():
            latest_collected_at = collect_task.start_at

        app_codes = UserApplicationFilter(request.user).filter().values_list("code", flat=True)
        reports = AppOperationReport.objects.filter(app__code__in=app_codes)

        issue_type_counts = reports.values("issue_type").annotate(count=Count("issue_type"))
        total = UserApplicationFilter(request.user).filter(include_inactive=True).count()

        data = {"collected_at": latest_collected_at, "issue_type_counts": issue_type_counts, "total": total}

        serializer = slzs.ApplicationEvaluationIssueCountListResultSLZ(data)
        return Response(serializer.data)


class ApplicationViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """View class for a single application."""

    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {
                "destroy": AppAction.DELETE_APPLICATION,
                "update": AppAction.EDIT_BASIC_INFO,
            },
            default_action=AppAction.VIEW_BASIC_INFO,
        ),
    ]

    def retrieve(self, request, code):
        """获取单个应用的信息"""
        application = self.get_application()

        main_role = fetch_user_main_role(code, request.user.username)
        product = application.get_product()

        web_config = application.config_info
        # We may not reuse this structure, so I will not make it a serializer
        return Response(
            {
                "role": slzs.RoleField().to_representation(main_role),
                "application": slzs.ApplicationSLZ(application).data,
                "product": slzs.ProductSLZ(product).data if product else None,
                "marked": UserMarkedApplication.objects.filter(
                    application=application, owner=request.user.pk
                ).exists(),
                "web_config": web_config,
                "migration_status": get_migration_process_status(application),
            }
        )

    def destroy(self, request, code):
        """删除蓝鲸应用

        - [测试地址](/api/bkapps/applications/{code}/)
        """
        application = self.get_application()

        market_config, _created = MarketConfig.objects.get_or_create_by_app(application)
        if market_config.enabled:
            raise error_codes.CANNOT_DELETE_APP.f(_("删除应用前, 请先从到「应用市场」下架该应用"))

        modules = application.modules.all()
        for module in modules:
            protection_status = ModuleDeletionPreparer(module).perform()
            if protection_status.activated:
                raise error_codes.CANNOT_DELETE_APP.f(protection_status.reason)

        # 云原生清理应用 BkApp crd
        if application.type == ApplicationType.CLOUD_NATIVE:
            for module in modules:
                envs = module.envs.all()
                for env in envs:
                    delete_bkapp(env)
                    delete_networking(env)

        try:
            with transaction.atomic():
                self._delete_all_module(application)
                self._delete_application(application)
        except Exception:
            logger.exception("unable to delete app<%s> related resources", application.code)
            # 执行失败
            add_app_audit_record(
                app_code=application.code,
                tenant_id=application.tenant_id,
                user=request.user.pk,
                action_id=AppAction.DELETE_APPLICATION,
                operation=OperationEnum.DELETE,
                target=OperationTarget.APP,
                result_code=ResultCode.FAILURE,
            )
            raise

        # 执行成功
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.DELETE_APPLICATION,
            operation=OperationEnum.DELETE,
            target=OperationTarget.APP,
            result_code=ResultCode.SUCCESS,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _delete_all_module(self, application: Application):
        try:
            delete_all_modules(application, self.request.user.pk)
        except Exception as e:
            logger.exception("unable to clean application related resources")
            raise error_codes.CANNOT_DELETE_APP.f(str(e))

    def _delete_application(self, application: Application):
        try:
            ApplicationCleaner(application).clean()
        except Exception as e:
            logger.exception(f"unable to delete application {application.code}")
            raise error_codes.CANNOT_DELETE_APP.f(str(e))

    # 编辑应用名称的权限：管理员、运营
    @transaction.atomic
    def update(self, request, code):
        """
        更新蓝鲸应用基本信息（应用名称）
        - [测试地址](/api/bkapps/applications/{code}/)
        - param: name, string, 应用名称
        - param: logo, file, 应用LOGO，不传则不更新
        """
        application = self.get_application()
        serializer = slzs.UpdateApplicationSLZ(data=request.data, instance=application)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # 仅修改对应语言的应用名称, 如果前端允许同时填写中英文的应用名称, 则可以去掉该逻辑.
        if get_language() == "zh-cn":
            application.name = data["name_zh_cn"]
        elif get_language() == "en":
            application.name_en = data["name_en"]
        application.save(update_fields=["name", "name_en"])

        ApplicationExtraInfo.objects.update_or_create(
            application=application,
            tenant_id=application.tenant_id,
            defaults={
                "tag_id": data["tag_id"],
                "availability_level": data.get("availability_level"),
            },
        )
        Product.objects.filter(code=code).update(name_zh_cn=application.name, name_en=application.name_en)

        # 应用 LOGO，不传则不更新
        if "logo" in request.data:
            logo_serializer = slzs.ApplicationLogoSLZ(data={"logo": request.data.get("logo")}, instance=application)
            logo_serializer.is_valid(raise_exception=True)
            logo_serializer.save()

        # 修改应用在蓝鲸监控命名空间的名称
        # 蓝鲸监控查询、更新一个不存在的应用返回的 code 都是 500，没有具体的错误码来标识是不是应用不存在，故直接调用更新API，忽略错误信息
        try:
            update_or_create_bk_monitor_space(application)
        except (BkMonitorGatewayServiceError, BkMonitorApiError) as e:
            logger.info(f"Failed to update app space on BK Monitor, {e}")
        except Exception:
            logger.exception("Failed to update app space on BK Monitor")
        # 审计记录
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.EDIT_BASIC_INFO,
            operation=OperationEnum.MODIFY_BASIC_INFO,
            target=OperationTarget.APP,
        )
        return Response(slzs.UpdateApplicationOutputSLZ(instance=application).data)

    @swagger_auto_schema(tags=["普通应用概览数据"])
    def get_overview(self, request, code):
        """普通应用、云原生应用概览页面数据"""
        application = self.get_application()
        data = get_app_overview(application)
        return Response(data)


class ApplicationExtraInfoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_secret(self, request, code):
        """获取单个应用的secret"""
        application = self.get_application()

        if settings.ENABLE_VERIFICATION_CODE:
            # 验证验证码
            serializer = VerificationCodeSLZ(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.data
            verifier = make_verifier(request.session, FunctionType.GET_APP_SECRET.value)
            is_valid = verifier.validate(data["verification_code"])
            if not is_valid:
                raise ValidationError({"verification_code": [_("验证码错误")]})
        else:
            logger.warning("Verification code is not currently supported, return app secret directly")

        client_secret = get_oauth2_client_secret(application.code)
        return Response({"app_code": application.code, "app_secret": client_secret})


class ApplicationFeatureFlagViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {
                "switch_app_desc_flag": AppAction.BASIC_DEVELOP,
            },
            default_action=AppAction.VIEW_BASIC_INFO,
        ),
    ]

    @swagger_auto_schema(tags=["特性标记"])
    def list(self, request, code):
        application = self.get_application()
        return Response(application.feature_flag.get_application_features())

    @swagger_auto_schema(tags=["特性标记"])
    def list_with_env(self, request, code, module_name, environment):
        """根据应用部署环境获取 FeatureFlag 信息，适用于需要区分环境的场景"""
        cluster = get_cluster_by_app(self.get_wl_app_via_path())
        response_data = {ff: cluster.has_feature_flag(ff) for ff in [ClusterFeatureFlag.ENABLE_AUTOSCALING]}
        return Response(response_data)

    @swagger_auto_schema(tags=["特性标记"])
    def switch_app_desc_flag(self, request, code):
        application = self.get_application()
        flag = AppFeatureFlag.APPLICATION_DESCRIPTION

        app_desc_enabled = application.feature_flag.has_feature(flag)
        if app_desc_enabled:
            raise_if_protected(application, ProtectedRes.DISABLE_APP_DESC)

        application.feature_flag.set_feature(flag, not app_desc_enabled)
        return Response({flag: application.feature_flag.has_feature(flag)})


class ApplicationResProtectionsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """查看应用的资源保护情况"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def list(self, request, code):
        """返回应用的资源保护状态"""
        application = self.get_application()
        statuses = AppResProtector(application).list_status()
        data = {name.value: slzs.ProtectionStatusSLZ(instance=data).data for name, data in statuses.items()}
        return Response(data)


class ApplicationLogoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for managing application's Logo"""

    serializer_class = slzs.ApplicationLogoSLZ

    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {
                "retrieve": AppAction.VIEW_BASIC_INFO,
                "update": AppAction.EDIT_BASIC_INFO,
            }
        ),
    ]

    def retrieve(self, request, code):
        """查看应用 Logo 相关信息"""
        serializer = slzs.ApplicationLogoSLZ(instance=self.get_application())
        return Response(serializer.data)

    def update(self, request, code):
        """修改应用 Logo"""
        application = self.get_application()
        serializer = slzs.ApplicationLogoSLZ(data=request.data, instance=application)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
