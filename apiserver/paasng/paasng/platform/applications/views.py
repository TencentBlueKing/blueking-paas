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

import base64
import logging
import random
import string
from collections import Counter, defaultdict
from io import BytesIO
from operator import itemgetter
from typing import Any, Dict, List, Optional, Set, Tuple

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db import IntegrityError as DbIntegrityError
from django.db import transaction
from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paas_wl.bk_app.cnative.specs.resource import delete_bkapp, delete_networking
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.shim import RegionClusterService
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.workloads.images.models import AppUserCredential
from paasng.accessories.publish.entrance.exposer import get_exposed_links
from paasng.accessories.publish.market.constant import AppState, ProductSourceUrlType
from paasng.accessories.publish.market.models import MarketConfig, Product
from paasng.accessories.publish.sync_market.managers import AppDeveloperManger
from paasng.core.core.storages.object_storage import app_logo_storage
from paasng.core.core.storages.sqlalchemy import legacy_db
from paasng.core.region.models import get_all_regions
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, get_tenant
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.constants import FunctionType
from paasng.infras.accounts.models import AccountFeatureFlag, make_verifier
from paasng.infras.accounts.permissions.application import app_action_required, application_perm_class
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_required
from paasng.infras.accounts.permissions.user import user_can_create_in_region
from paasng.infras.accounts.serializers import VerificationCodeSLZ
from paasng.infras.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError
from paasng.infras.bkmonitorv3.shim import update_or_create_bk_monitor_space
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.helpers import (
    add_role_members,
    fetch_application_members,
    fetch_role_members,
    fetch_user_main_role,
    remove_user_all_roles,
)
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.misc.audit import constants
from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications import serializers as slzs
from paasng.platform.applications.cleaner import ApplicationCleaner, delete_all_modules
from paasng.platform.applications.constants import (
    AppFeatureFlag,
    ApplicationRole,
    ApplicationType,
    LightApplicationViewSetErrorCode,
)
from paasng.platform.applications.exceptions import IntegrityError, LightAppAPIError
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import (
    Application,
    ApplicationDeploymentModuleOrder,
    ApplicationEnvironment,
    JustLeaveAppManager,
    UserApplicationFilter,
    UserMarkedApplication,
)
from paasng.platform.applications.pagination import ApplicationListPagination
from paasng.platform.applications.protections import AppResProtector, ProtectedRes, raise_if_protected
from paasng.platform.applications.serializers import ApplicationMemberRoleOnlySLZ, ApplicationMemberSLZ
from paasng.platform.applications.signals import application_member_updated, post_create_application
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.platform.applications.tenant import validate_app_tenant_params
from paasng.platform.applications.utils import (
    create_application,
    create_default_module,
    create_market_config,
    create_third_app,
    get_app_overview,
)
from paasng.platform.bk_lesscode.client import make_bk_lesscode_client
from paasng.platform.bk_lesscode.exceptions import LessCodeApiError, LessCodeGatewayServiceError
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import (
    AppOperationReport,
    AppOperationReportCollectionTask,
    IdleAppNotificationMuteRule,
)
from paasng.platform.mgrlegacy.constants import LegacyAppState
from paasng.platform.mgrlegacy.migrate import get_migration_process_status
from paasng.platform.modules.constants import ExposedURLType, ModuleName, SourceOrigin
from paasng.platform.modules.manager import init_module_in_view
from paasng.platform.modules.models.module import Module
from paasng.platform.modules.protections import ModuleDeletionPreparer
from paasng.platform.scene_app.initializer import SceneAPPInitializer
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.utils import dictx
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.error_codes import error_codes

try:
    from paasng.infras.legacydb_te.adaptors import AppAdaptor, AppTagAdaptor
    from paasng.infras.legacydb_te.models import get_developers_by_v2_application
except ImportError:
    from paasng.infras.legacydb.adaptors import AppAdaptor, AppTagAdaptor  # type: ignore
    from paasng.infras.legacydb.models import get_developers_by_v2_application  # type: ignore

logger = logging.getLogger(__name__)


class ApplicationListViewSet(viewsets.ViewSet):
    """View class for application lists."""

    @swagger_auto_schema(query_serializer=slzs.ApplicationListDetailedSLZ)
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

        # 查询我创建的应用时，也需要返回总的应用数量给前端
        all_app_count = applications.count()
        # 仅查询我创建的应用
        if params.get("exclude_collaborated") is True:
            applications = applications.filter(owner=request.user.pk)

        # 插件开发者中心正式上线前需要根据配置来决定应用列表中是否展示插件应用
        if not settings.DISPLAY_BK_PLUGIN_APPS:
            applications = applications.filter(is_plugin_app=False)

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

    @swagger_auto_schema(query_serializer=slzs.ApplicationListMinimalSLZ)
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

    @swagger_auto_schema(query_serializer=slzs.SearchApplicationSLZ)
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
        query_serializer=slzs.ApplicationEvaluationListQuerySLZ,
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

    @app_action_required(AppAction.VIEW_BASIC_INFO)
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

    @app_action_required(AppAction.DELETE_APPLICATION)
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
    @app_action_required(AppAction.EDIT_BASIC_INFO)
    @transaction.atomic
    def update(self, request, code):
        """
        更新蓝鲸应用基本信息（应用名称）
        - [测试地址](/api/bkapps/applications/{code}/)
        - param: name, string, 应用名称
        - param: logo, file, 应用LOGO，不传则不更新
        """
        application = self.get_application()
        # Check if app was protected
        raise_if_protected(application, ProtectedRes.BASIC_INFO_MODIFICATIONS)

        serializer = slzs.UpdateApplicationSLZ(data=request.data, instance=application)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
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
        return Response(serializer.data)

    @app_action_required(AppAction.VIEW_BASIC_INFO)
    @swagger_auto_schema(tags=["普通应用概览数据"])
    def get_overview(self, request, code):
        """普通应用、云原生应用概览页面数据"""
        application = self.get_application()
        data = get_app_overview(application)
        return Response(data)


class ApplicationCreateViewSet(viewsets.ViewSet):
    serializer_class = None
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=slzs.CreateThirdPartyApplicationSLZ, tags=["创建应用"])
    def create_third_party(self, request):
        """[API] 创建第三方应用(外链应用)"""
        serializer = slzs.CreateThirdPartyApplicationSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        self.validate_region_perm(data["region"])

        market_params = data["market_params"]
        operator = request.user.pk

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, data["app_tenant_mode"])
        try:
            application = create_third_app(
                data["region"],
                data["code"],
                data["name_zh_cn"],
                data["name_en"],
                operator,
                app_tenant_mode,
                app_tenant_id,
                tenant.id,
                market_params,
            )
        except DbIntegrityError as e:
            # 并发创建时, 可能会绕过 CreateThirdPartyApplicationSLZ 中 code 和 name 的存在性校验
            if "Duplicate entry" in str(e):
                err_msg = _("code 为 {} 或 name 为 {} 的应用已存在").format(data["code"], data["name_zh_cn"])
                raise error_codes.CANNOT_CREATE_APP.f(err_msg)
            raise

        return Response(
            data={"application": slzs.ApplicationSLZ(application).data, "source_init_result": None},
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateApplicationV2SLZ, tags=["创建应用"])
    def create_v2(self, request):
        """[API] 创建新的蓝鲸应用（v2 版），支持更多自定义参数
        创建 lesscode 应用时需要从cookie中获取用户登录信息,该 APIGW 不能直接注册到 APIGW 上提供"""
        serializer = slzs.CreateApplicationV2SLZ(data=request.data, context={"region": request.data["region"]})
        serializer.is_valid(raise_exception=True)
        params = serializer.data
        if not params["engine_enabled"]:
            return self.create_third_party(request)

        self.validate_region_perm(params["region"])
        # Handle advanced options
        advanced_options = params.get("advanced_options", {})
        cluster_name = None
        if advanced_options:
            # Permission check
            if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS):
                raise ValidationError(_("你无法使用高级创建选项"))

            cluster_name = advanced_options.get("cluster_name")

        engine_params = params.get("engine_params", {})
        source_origin = SourceOrigin(engine_params["source_origin"])
        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, params["app_tenant_mode"])
        # Guide: check if a bk_plugin can be created
        if params["is_plugin_app"] and not settings.IS_ALLOW_CREATE_BK_PLUGIN_APP:
            raise ValidationError(_("当前版本下无法创建蓝鲸插件应用"))

        if source_origin == SourceOrigin.SCENE:
            return self._init_scene_app(request, app_tenant_mode, app_tenant_id, tenant.id, params, engine_params)

        # lesscode app needs to create an application on the bk_lesscode platform first
        if source_origin == SourceOrigin.BK_LESS_CODE:
            bk_token = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
            try:
                # 目前页面创建的应用名称都存储在 name_zh_cn 字段中, name_en 只用于 smart 应用
                make_bk_lesscode_client(login_cookie=bk_token, tenant_id=get_tenant(request.user).id).create_app(
                    params["code"], params["name_zh_cn"], ModuleName.DEFAULT.value
                )
            except (LessCodeApiError, LessCodeGatewayServiceError) as e:
                raise error_codes.CREATE_LESSCODE_APP_ERROR.f(e.message)

        return self._init_normal_app(
            params,
            engine_params,
            source_origin,
            cluster_name,
            request.user.pk,
            app_tenant_mode,
            app_tenant_id,
            tenant.id,
        )

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateApplicationV2SLZ, tags=["创建蓝鲸可视化开发平台应用"])
    def create_lesscode_app(self, request):
        """注册在 APIGW 上给 bk_lesscode 平台调用，调用参数如下:
        {
            "region": "default",
            "code": "lesscode2",
            "name": "lesscode2",

            // 下面这些参数保持这些默认值就好了
            "type": "default",
            "engine_enabled": true,
            "engine_params": {
                "source_origin": 2,
                "source_init_template": "nodejs_bk_magic_vue_spa2"
            }
        }
        """
        # 根据配置判断新建的 lesscode 应用是否为云原生应用
        if settings.LESSCODE_APP_USE_CLOUD_NATIVE_TYPE:
            serializer_class = slzs.CreateCloudNativeApplicationSLZ
        else:
            serializer_class = slzs.CreateApplicationV2SLZ

        serializer = serializer_class(data=request.data, context={"region": request.data["region"]})
        serializer.is_valid(raise_exception=True)
        params = serializer.data
        self.validate_region_perm(params["region"])

        engine_params = params.get("engine_params", {})

        source_origin = SourceOrigin(engine_params["source_origin"])
        cluster_name = None

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, params["app_tenant_mode"])
        return self._init_normal_app(
            params,
            engine_params,
            source_origin,
            cluster_name,
            request.user.pk,
            app_tenant_mode,
            app_tenant_id,
            tenant.id,
        )

    def _create_app_in_lesscode(self, request, code: str, name: str):
        """在开发者中心产品页面上创建 Lesscode 应用时，需要同步在 Lesscode 产品上创建应用"""
        bk_token = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
        try:
            make_bk_lesscode_client(login_cookie=bk_token, tenant_id=get_tenant(request.user).id).create_app(
                code, name, ModuleName.DEFAULT.value
            )
        except (LessCodeApiError, LessCodeGatewayServiceError) as e:
            raise error_codes.CREATE_LESSCODE_APP_ERROR.f(e.message)

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateCloudNativeAppSLZ, tags=["创建应用"])
    def create_cloud_native(self, request):
        """[API] 创建云原生架构应用"""
        serializer = slzs.CreateCloudNativeAppSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        self.validate_region_perm(params["region"])

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, params["app_tenant_mode"])

        advanced_options = params.get("advanced_options", {})
        cluster_name = None
        if advanced_options:
            if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS):
                raise ValidationError(_("你无法使用高级创建选项"))
            cluster_name = advanced_options.get("cluster_name")

        module_src_cfg: Dict[str, Any] = {"source_origin": SourceOrigin.CNATIVE_IMAGE}
        source_config = params["source_config"]
        source_origin = SourceOrigin(source_config["source_origin"])

        # Guide: check if a bk_plugin can be created
        if params["is_plugin_app"] and not settings.IS_ALLOW_CREATE_BK_PLUGIN_APP:
            raise ValidationError(_("当前版本下无法创建蓝鲸插件应用"))

        module_src_cfg["source_origin"] = source_origin
        # 如果指定模板信息，则需要提取并保存
        if tmpl_name := source_config["source_init_template"]:
            tmpl = Template.objects.get(name=tmpl_name)
            module_src_cfg.update({"language": tmpl.language, "source_init_template": tmpl_name})
        # lesscode app needs to create an application on the bk_lesscode platform first
        if source_origin == SourceOrigin.BK_LESS_CODE:
            # 目前页面创建的应用名称都存储在 name_zh_cn 字段中, name_en 只用于 smart 应用
            self._create_app_in_lesscode(request, params["code"], params["name_zh_cn"])

        application = create_application(
            region=params["region"],
            code=params["code"],
            name=params["name_zh_cn"],
            name_en=params["name_en"],
            type_=ApplicationType.CLOUD_NATIVE.value,
            operator=request.user.pk,
            is_plugin_app=params["is_plugin_app"],
            app_tenant_mode=app_tenant_mode,
            app_tenant_id=app_tenant_id,
            tenant_id=tenant.id,
        )
        module = create_default_module(application, **module_src_cfg)

        # 初始化应用镜像凭证信息
        if image_credential := params["bkapp_spec"]["build_config"].image_credential:
            self._init_image_credential(application, image_credential)

        source_init_result = init_module_in_view(
            module,
            repo_type=source_config.get("source_control_type"),
            repo_url=source_config.get("source_repo_url"),
            repo_auth_info=source_config.get("source_repo_auth_info"),
            source_dir=source_config.get("source_dir", ""),
            cluster_name=cluster_name,
            bkapp_spec=params["bkapp_spec"],
        ).source_init_result

        https_enabled = self._get_cluster_entrance_https_enabled(
            module.region, cluster_name, ExposedURLType(module.exposed_url_type)
        )

        post_create_application.send(sender=self.__class__, application=application)
        create_market_config(
            application=application,
            # 当应用开启引擎时, 则所有访问入口都与 Prod 一致
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
            # 对于新创建的应用, 如果集群支持 HTTPS, 则默认开启 HTTPS
            prefer_https=https_enabled,
        )
        return Response(
            data={"application": slzs.ApplicationSLZ(application).data, "source_init_result": source_init_result},
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateAIAgentAppSLZ, tags=["ai-agent-app"])
    def create_ai_agent_app(self, request):
        """创建 AI Agent 插件应用"""
        serializer = slzs.CreateAIAgentAppSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        self.validate_region_perm(params["region"])

        source_origin = SourceOrigin.AI_AGENT
        engine_params = {
            "source_origin": source_origin,
            # TODO AI agent 还没有提供模板，目前是直接使用 Python 插件的模板
            "source_init_template": "bk-saas-plugin-python",
        }
        cluster_name = None
        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, params["app_tenant_mode"])
        return self._init_normal_app(
            params,
            engine_params,
            source_origin,
            cluster_name,
            request.user.pk,
            app_tenant_mode,
            app_tenant_id,
            tenant.id,
        )

    def get_creation_options(self, request):
        """[API] 获取创建应用模块时的选项信息"""
        # 是否允许用户使用高级选项
        allow_advanced = AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS)
        adv_region_clusters = []
        if allow_advanced:
            for region_name in get_all_regions():
                clusters = RegionClusterService(region_name).list_clusters()
                adv_region_clusters.append(
                    {"region": region_name, "cluster_names": [cluster.name for cluster in clusters]}
                )

        options = {
            # ADVANCED options:
            "allow_adv_options": allow_advanced,
            # configs related with clusters, contains content only when "allow_adv_options" is true
            "adv_region_clusters": adv_region_clusters,
        }
        return Response(options)

    def validate_region_perm(self, region: str):
        if not user_can_create_in_region(self.request.user, region):
            raise error_codes.CANNOT_CREATE_APP.f(_("你无法在所指定的 region 中创建应用"))

    def _get_cluster_entrance_https_enabled(
        self, region: str, cluster_name: Optional[str], exposed_url_type: ExposedURLType
    ) -> bool:
        if not cluster_name:
            cluster = RegionClusterService(region).get_default_cluster()
        else:
            cluster = RegionClusterService(region).get_cluster_by_name(cluster_name)

        try:
            if exposed_url_type == ExposedURLType.SUBDOMAIN:
                return cluster.ingress_config.default_root_domain.https_enabled
            else:
                return cluster.ingress_config.default_sub_path_domain.https_enabled
        except IndexError:
            # exposed_url_type == SUBDOMAIN 的集群, 应当配置 default_root_domain
            # exposed_url_type == SUBPATH 的集群, 应当配置 default_sub_path_domain
            logger.warning(_("集群未配置默认的根域名, 请检查 region=%s 下的集群配置是否合理."), region)
            return False

    def _init_normal_app(
        self,
        params: Dict,
        engine_params: Dict,
        source_origin: SourceOrigin,
        cluster_name: Optional[str],
        operator: str,
        app_tenant_mode: AppTenantMode = AppTenantMode.GLOBAL,
        app_tenant_id: str = "",
        tenant_id: str = DEFAULT_TENANT_ID,
    ) -> Response:
        """初始化应用，包含创建默认模块，应用市场配置等"""
        application = create_application(
            region=params["region"],
            code=params["code"],
            name=params["name_zh_cn"],
            name_en=params["name_en"],
            type_=params["type"],
            is_plugin_app=params["is_plugin_app"],
            is_ai_agent_app=params["is_ai_agent_app"],
            operator=operator,
            app_tenant_mode=app_tenant_mode,
            app_tenant_id=app_tenant_id,
            tenant_id=tenant_id,
        )

        # Create engine related data
        # `source_init_template` is optional
        source_init_template = engine_params.get("source_init_template", "")
        language = ""
        if source_init_template:
            language = Template.objects.get(
                name=source_init_template, type__in=TemplateType.normal_app_types()
            ).language
        module = create_default_module(
            application,
            source_init_template=source_init_template,
            language=language,
            source_origin=source_origin,
        )
        source_init_result = init_module_in_view(
            module,
            repo_type=engine_params.get("source_control_type"),
            repo_url=engine_params.get("source_repo_url"),
            repo_auth_info=engine_params.get("source_repo_auth_info"),
            source_dir=engine_params.get("source_dir"),
            cluster_name=cluster_name,
        ).source_init_result

        https_enabled = self._get_cluster_entrance_https_enabled(
            module.region, cluster_name, ExposedURLType(module.exposed_url_type)
        )

        if language:
            application.language = language
            application.save(update_fields=["language"])

        post_create_application.send(sender=self.__class__, application=application)
        create_market_config(
            application=application,
            # 当应用开启引擎时, 则所有访问入口都与 Prod 一致
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
            # 对于新创建的应用, 如果集群支持 HTTPS, 则默认开启 HTTPS
            prefer_https=https_enabled,
        )

        return Response(
            data={"application": slzs.ApplicationSLZ(application).data, "source_init_result": source_init_result},
            status=status.HTTP_201_CREATED,
        )

    def _init_scene_app(
        self, request, app_tenant_mode: str, app_tenant_id: str, tenant_id: str, params: Dict, engine_params: Dict
    ) -> Response:
        """初始化场景 SaaS 应用，包含根据 app_desc 文件创建一或多个模块，配置应用市场配置等"""
        tmpl_name = engine_params.get("source_init_template", "")
        app_name, app_code, region = params["name_en"], params["code"], params["region"]

        try:
            application, result = SceneAPPInitializer(
                request.user,
                tmpl_name,
                app_name,
                app_code,
                region,
                app_tenant_mode,
                app_tenant_id,
                tenant_id,
                engine_params,
            ).execute()
        except DescriptionValidationError as e:
            logger.exception("Invalid app_desc.yaml cause create app failed")
            raise error_codes.SCENE_TMPL_DESC_ERROR.f(e.message)
        except ControllerError as e:
            logger.exception("Controller error cause create app failed")
            raise error_codes.CANNOT_CREATE_APP.f(e.message)

        source_init_result: Dict[str, Any] = {"code": result.error}
        if result.is_success():
            source_init_result = {"code": "OK", "extra_info": result.extra_info, "dest_type": result.dest_type}

        return Response(
            data={
                "application": slzs.ApplicationSLZ(application).data,
                "source_init_result": source_init_result,
            },
            status=status.HTTP_201_CREATED,
        )

    def _init_image_credential(self, application: Application, image_credential: Dict):
        try:
            AppUserCredential.objects.create(
                application_id=application.id, tenant_id=application.tenant_id, **image_credential
            )
        except DbIntegrityError:
            raise error_codes.CREATE_CREDENTIALS_FAILED.f(_("同名凭证已存在"))


class ApplicationMembersViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """Viewset for application members management"""

    pagination_class = None
    permission_classes = [IsAuthenticated]

    @app_action_required(AppAction.VIEW_BASIC_INFO)
    def list(self, request, **kwargs):
        """Always add 'result' key in response"""
        members = fetch_application_members(self.get_application().code)
        return Response({"results": ApplicationMemberSLZ(members, many=True).data})

    @app_action_required(AppAction.MANAGE_MEMBERS)
    def create(self, request, **kwargs):
        application = self.get_application()

        serializer = ApplicationMemberSLZ(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        role_members_map = defaultdict(list)
        for info in serializer.data:
            for role in info["roles"]:
                role_members_map[role["id"]].append(info["user"]["username"])

        try:
            for role, members in role_members_map.items():
                add_role_members(application.code, role, members)
        except BKIAMGatewayServiceError as e:
            raise error_codes.CREATE_APP_MEMBERS_ERROR.f(e.message)

        application_member_updated.send(sender=application, application=application)
        sync_developers_to_sentry.delay(application.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @app_action_required(AppAction.MANAGE_MEMBERS)
    def update(self, request, *args, **kwargs):
        application = self.get_application()

        serializer = ApplicationMemberRoleOnlySLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = get_username_by_bkpaas_user_id(kwargs["user_id"])
        self.check_admin_count(application.code, username)
        try:
            remove_user_all_roles(application.code, username)
            add_role_members(application.code, ApplicationRole(serializer.data["role"]["id"]), username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.UPDATE_APP_MEMBERS_ERROR.f(e.message)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @app_action_required(AppAction.VIEW_BASIC_INFO)
    def leave(self, request, *args, **kwargs):
        application = self.get_application()

        self.check_admin_count(application.code, request.user.username)
        try:
            remove_user_all_roles(application.code, request.user.username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.DELETE_APP_MEMBERS_ERROR.f(e.message)

        # 将该应用 Code 标记为刚退出，避免出现退出用户组，权限中心权限未同步的情况
        JustLeaveAppManager(request.user.username).add(application.code)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @app_action_required(AppAction.MANAGE_MEMBERS)
    def destroy(self, request, *args, **kwargs):
        application = self.get_application()

        username = get_username_by_bkpaas_user_id(kwargs["user_id"])
        self.check_admin_count(application.code, username)
        try:
            remove_user_all_roles(application.code, username)
        except BKIAMGatewayServiceError as e:
            raise error_codes.DELETE_APP_MEMBERS_ERROR.f(e.message)

        # 将该应用 Code 标记为刚退出，避免出现退出用户组，权限中心权限未同步的情况
        JustLeaveAppManager(username).add(application.code)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def check_admin_count(self, app_code: str, username: str):
        # Check whether the application has at least one administrator when the membership was deleted
        administrators = fetch_role_members(app_code, ApplicationRole.ADMINISTRATOR)
        if len(administrators) <= 1 and username in administrators:
            raise error_codes.MEMBERSHIP_DELETE_FAILED

    def get_roles(self, request):
        return Response({"results": ApplicationRole.get_django_choices()})


class ApplicationMarkedViewSet(viewsets.ModelViewSet):
    """
    用户标记的应用
    list: 获取用户标记的应用列表
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    create: 添加标记应用
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    retrieve: 获取标记详情
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    destroy: 删除标记
    - [测试地址](/api/bkapps/accounts/marked_applications/)
    """

    lookup_field = "code"
    serializer_class = slzs.ApplicationMarkedSLZ
    queryset = UserMarkedApplication.objects.all()
    pagination_class = None

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user.pk)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {"application__code": self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class ApplicationGroupByStateStatisticsView(APIView):
    def get(self, request):
        """
        应用视图接口-按应用状态分组
        - [测试地址](/api/bkapps/applications/statistics/group_by_state/)
        """
        application_queryset = Application.objects.filter_by_user(request.user)
        applications_ids = application_queryset.values_list("id", flat=True)
        queryset = ApplicationEnvironment.objects.filter(application__id__in=applications_ids)
        never_deployed = queryset.filter(deployments__isnull=True, environment="stag").values("id").distinct().count()

        # 预发布环境的应用, 需要排除同时部署过预发布环境和正式环境的应用
        prod_deployed_ids = queryset.filter(is_offlined=False, deployments__isnull=False, environment="prod").values(
            "id"
        )
        stag_deployed = (
            queryset.filter(is_offlined=False, deployments__isnull=False, environment="stag")
            .exclude(id__in=prod_deployed_ids)
            .values("id")
            .distinct()
            .count()
        )

        prod_deployed = (
            queryset.filter(is_offlined=False, deployments__isnull=False, environment="prod")
            .values("id")
            .distinct()
            .count()
        )

        onlined_market = application_queryset.filter(product__state=AppState.RELEASED.value).count()

        offlined_counts = application_queryset.filter(is_active=False).count()

        data = [
            {"name": _("开发中"), "count": never_deployed, "group": "developing"},
            {"name": _("预发布环境"), "count": stag_deployed, "group": "stag"},
            {"name": _("生产环境"), "count": prod_deployed, "group": "prod"},
            {"name": _("应用市场"), "count": onlined_market, "group": "product"},
            {"name": _("已下架"), "count": offlined_counts, "group": "offline"},
        ]
        return Response({"data": data})


class ApplicationGroupByFieldStatisticsView(APIView):
    def get(self, request):
        """
        应用概览-按某个App字段聚合分类
        - [测试地址](/api/bkapps/applications/summary/group_by_field/)
        ----
        {
            "200": {
                "description": "获取应用概览信息成功",
                "schema": {
                    "type": "object",
                    "properties": {
                        "total": {
                            "type": "integer",
                            "description": "应用总数",
                            "example": 23
                        },
                        {
                            "groups": [
                                {"count": 4, "region": "clouds"},
                                {"count": 5, "region": "tencent"},
                                {"count": 10, "region": "ieod"}],
                            "total": 19
                        }
                    }
                }
            }
        }
        """

        serializer = slzs.ApplicationGroupFieldSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        params = serializer.data
        include_inactive = params["include_inactive"]
        group_field = params["field"]

        queryset = Application.objects.filter_by_user(request.user)
        # 从用户角度来看，应用分类需要区分是否为已删除应用
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        application_group = queryset.values_list(group_field, flat=True)
        counter: Dict[str, int] = Counter(application_group)
        groups = [{group_field: group, "count": count} for group, count in list(counter.items())]
        # sort by count
        sorted_groups = sorted(groups, key=itemgetter("count"), reverse=True)
        data = {"total": queryset.count(), "groups": sorted_groups}
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
    @swagger_auto_schema(tags=["特性标记"])
    @app_action_required(AppAction.VIEW_BASIC_INFO)
    def list(self, request, code):
        application = self.get_application()
        return Response(application.feature_flag.get_application_features())

    @swagger_auto_schema(tags=["特性标记"])
    @app_action_required(AppAction.VIEW_BASIC_INFO)
    def list_with_env(self, request, code, module_name, environment):
        """根据应用部署环境获取 FeatureFlag 信息，适用于需要区分环境的场景"""
        cluster = get_cluster_by_app(self.get_wl_app_via_path())
        response_data = {ff: cluster.has_feature_flag(ff) for ff in [ClusterFeatureFlag.ENABLE_AUTOSCALING]}
        return Response(response_data)

    @swagger_auto_schema(tags=["特性标记"])
    @app_action_required(AppAction.BASIC_DEVELOP)
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


class LightAppViewSet(viewsets.ViewSet):
    """为标准运维提供轻应用管理接口，部分代码迁移自 open—paas"""

    @site_perm_required(SiteAction.SYSAPI_MANAGE_LIGHT_APPLICATIONS)
    @swagger_auto_schema(request_body=slzs.LightAppCreateSLZ)
    def create(self, request):
        """创建轻应用"""
        slz = slzs.LightAppCreateSLZ(data=request.data)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            tag_manager = AppTagAdaptor(session=session)
            parent_app = app_manager.get(code=data["parent_app_code"])

            if not parent_app:
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message="parent_app_code is illegal"
                )

            app_code = self.get_available_light_app_code(session, parent_app.code)
            if not app_code:
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message="generate app_code failed"
                )

            tag = tag_manager.get(code=data["tag"])
            logo_content = data.get("logo")
            if logo_content:
                logo_url = self.store_logo(app_code, logo_content)
            else:
                logo_url = ""

            app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, data["app_tenant_mode"])
            try:
                light_app = AppAdaptor(session=session).create(
                    code=app_code,
                    name=data["name"],
                    app_tenant_mode=app_tenant_mode,
                    app_tenant_id=app_tenant_id,
                    tenant_id=tenant.id,
                    logo=logo_url,
                    is_lapp=True,
                    creator=data["creator"],
                    tag=tag,
                    height=data.get("height") or parent_app.height,
                    width=data.get("width") or parent_app.width,
                    external_url=data["external_url"],
                    deploy_ver=settings.DEFAULT_REGION_NAME,
                    introduction=data.get("introduction"),
                    state=LegacyAppState.ONLINE.value,
                    is_already_test=1,
                    is_already_online=1,
                )
            except IntegrityError as e:
                logger.exception("Create lapp %s(%s) failed!", data["name"], app_code)
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR,
                    message=f"app with the same {e.field} already exists.",
                )
            except Exception as e:
                logger.exception("save app base info fail.")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                ) from e

            try:
                AppDeveloperManger(session=session).update_developers(
                    code=light_app.code, target_developers=data["developers"]
                )
            except Exception:
                logger.exception("同步开发者信息到桌面失败！")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                )

            return self.make_app_response(session, light_app)

    @site_perm_required(SiteAction.SYSAPI_MANAGE_LIGHT_APPLICATIONS)
    @swagger_auto_schema(query_serializer=slzs.LightAppDeleteSLZ)
    def delete(self, request):
        """软删除轻应用"""
        slz = slzs.LightAppDeleteSLZ(data=request.query_params)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            app = self.validate_app(app_manager.get(data["light_app_code"]))

            try:
                app_manager.soft_delete(code=app.code)
            except Exception:
                logger.exception("save app base info fail.")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                )

        return self.make_feedback_response(LightApplicationViewSetErrorCode.SUCCESS, data={"count": 1})

    @site_perm_required(SiteAction.SYSAPI_MANAGE_LIGHT_APPLICATIONS)
    @swagger_auto_schema(request_body=slzs.LightAppEditSLZ)
    def edit(self, request):
        """修改轻应用"""
        slz = slzs.LightAppEditSLZ(data=request.data, partial=True)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            tag_manager = AppTagAdaptor(session=session)
            app = self.validate_app(app_manager.get(data["code"]))

            tag = tag_manager.get(code=data.pop("tag", None))
            logo_content = data.get("logo")
            if logo_content:
                data["logo"] = self.store_logo(app.code, logo_content)

            if tag:
                data["tags_id"] = tag.id

            developers = data.pop("developers", None)

            try:
                app_manager.update(app.code, data)
            except Exception:
                logger.exception("save app base info fail.")
                raise LightAppAPIError(
                    LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="edit light app failed"
                )

            if developers:
                try:
                    AppDeveloperManger(session=session).update_developers(code=app.code, target_developers=developers)
                except Exception:
                    logger.exception("同步开发者信息到桌面失败！")
                    raise LightAppAPIError(
                        LightApplicationViewSetErrorCode.CREATE_APP_ERROR, message="create light app failed"
                    )

            return self.make_app_response(session, app)

    @site_perm_required(SiteAction.SYSAPI_MANAGE_LIGHT_APPLICATIONS)
    @swagger_auto_schema(query_serializer=slzs.LightAppQuerySLZ)
    def query(self, request):
        """查询轻应用"""
        slz = slzs.LightAppQuerySLZ(data=request.query_params)
        if not slz.is_valid():
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=slz.errors)

        data = slz.validated_data
        with legacy_db.session_scope() as session:
            app_manager = AppAdaptor(session=session)
            app = self.validate_app(app_manager.get(data["light_app_code"]))

            return self.make_app_response(session, app)

    def handle_exception(self, exc):
        """统一异常处理, 将 LightAppAPIError 转换成 Response"""
        if isinstance(exc, LightAppAPIError):
            return self.make_feedback_response(
                code=exc.error_code,
                message=exc.message,
            )

        return super().handle_exception(exc)

    @classmethod
    def generate_app_maker_code(cls, parent_code):
        """
        生成轻应用 ID
        """
        alphabet = string.digits + string.ascii_lowercase

        # 轻应用的 app code 根据约定长度为 15
        # 为保证可创建的轻应用足够多(至少 36 * 36 个), 至少保留 2 位由随机字符生成
        parent_code = parent_code[:13]
        salt = "".join(random.choices(alphabet, k=15 - len(parent_code)))
        return f"{parent_code}_{salt}"

    @classmethod
    def get_available_light_app_code(cls, session, parent_code, max_times=10):
        app_manager = AppAdaptor(session=session)
        for __ in range(max_times):
            app_code = cls.generate_app_maker_code(parent_code)
            if not app_manager.get(app_code):
                return app_code
        return None

    @staticmethod
    def store_logo(app_code, logo: str):
        """将 base64 编码后的图片存储至 AppLogoStorage, 并刷新 storage 的缓存.
        :param app_code: 轻应用ID
        :param logo: base64 编码后的图片内容
        :return:
        """
        if not logo:
            return ""

        logo_name = f"o_{app_code}.png"  # 轻应用 logo 规则
        logo_file = BytesIO(base64.b64decode(logo))
        app_logo_storage.save(logo_name, logo_file)
        bucket = settings.APP_LOGO_BUCKET
        try:
            from paasng.platform.applications.handlers import initialize_app_logo_metadata

            initialize_app_logo_metadata(Application._meta.get_field("logo").storage, bucket, logo_name)
        except Exception:
            logger.exception("Fail to update logo cache.")
        return app_logo_storage.url(logo_name)

    def make_app_response(self, session, app):
        return self.make_feedback_response(
            LightApplicationViewSetErrorCode.SUCCESS,
            data={
                "light_app_code": app.code,
                "app_name": app.name,
                "app_url": app.external_url,
                "introduction": app.introduction,
                "creator": app.creater,
                "logo": app.logo,
                "developers": sorted(get_developers_by_v2_application(app, session)),
                "state": app.state,
            },
        )

    def make_feedback_response(self, code, data=None, message=""):
        return Response(
            {
                "bk_error_msg": message,
                "bk_error_code": code.value,
                "data": data,
                "result": data is not None,
            }
        )

    @staticmethod
    def validate_app(app):
        if not app or not app.is_lapp:
            raise LightAppAPIError(LightApplicationViewSetErrorCode.PARAM_NOT_VALID, message=f"{app.code} not found")
        return app


class ApplicationLogoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for managing application's Logo"""

    serializer_class = slzs.ApplicationLogoSLZ

    @app_action_required(AppAction.VIEW_BASIC_INFO)
    def retrieve(self, request, code):
        """查看应用 Logo 相关信息"""
        serializer = slzs.ApplicationLogoSLZ(instance=self.get_application())
        return Response(serializer.data)

    @app_action_required(AppAction.EDIT_BASIC_INFO)
    def update(self, request, code):
        """修改应用 Logo"""
        application = self.get_application()
        serializer = slzs.ApplicationLogoSLZ(data=request.data, instance=application)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SysAppViewSet(viewsets.ViewSet):
    @site_perm_required(SiteAction.SYSAPI_MANAGE_APPLICATIONS)
    @swagger_auto_schema(request_body=slzs.SysThirdPartyApplicationSLZ, tags=["创建第三方(外链)应用"])
    def create_sys_third_app(self, request, sys_id):
        """给特定系统提供的创建第三方应用的 API, 应用ID 必现以系统ID为前缀"""
        serializer = slzs.SysThirdPartyApplicationSLZ(data=request.data, context={"sys_id": sys_id})
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        operator = user_id_encoder.encode(settings.USER_TYPE, data["operator"])

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(request.user, data["app_tenant_mode"])
        application = create_third_app(
            data["region"],
            data["code"],
            data["name_zh_cn"],
            data["name_en"],
            operator,
            app_tenant_mode,
            app_tenant_id,
            tenant.id,
        )
        # 返回应用的密钥信息
        secret = get_oauth2_client_secret(application.code)
        return Response(
            data={"bk_app_code": application.code, "bk_app_secret": secret},
            status=status.HTTP_201_CREATED,
        )


class ApplicationDeploymentModuleOrderViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """部署管理-进程列表，模块的排序"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(request_body=slzs.ApplicationDeploymentModuleOrderReqSLZ)
    @transaction.atomic
    def upsert(self, request, code):
        """设置模块的排序"""
        serializer = slzs.ApplicationDeploymentModuleOrderReqSLZ(data=request.data, context={"code": code})
        serializer.is_valid(raise_exception=True)
        module_orders_data = serializer.validated_data["module_orders"]

        application = self.get_application()
        modules = Module.objects.filter(application=application)
        module_name_to_module_dict = {module.name: module for module in modules}

        # 操作前
        old_module_orders = list(
            ApplicationDeploymentModuleOrder.objects.filter(user=request.user.pk, module__application=application)
            .order_by("order")
            .values("order", module_name=F("module__name"))
        )

        # 更新或创建模块排序
        for item in module_orders_data:
            ApplicationDeploymentModuleOrder.objects.update_or_create(
                user=request.user.pk,
                module=module_name_to_module_dict[item["module_name"]],
                defaults={
                    "order": item["order"],
                    "tenant_id": application.tenant_id,
                },
            )

        # 操作后
        new_module_orders = list(
            ApplicationDeploymentModuleOrder.objects.filter(user=request.user.pk, module__application=application)
            .order_by("order")
            .values("order", module_name=F("module__name"))
        )

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.MODULE,
            result_code=ResultCode.SUCCESS,
            data_before=DataDetail(type=constants.DataType.RAW_DATA, data=old_module_orders),
            data_after=DataDetail(type=constants.DataType.RAW_DATA, data=new_module_orders),
        )

        serializer = slzs.ApplicationDeploymentModuleOrderSLZ(new_module_orders, many=True)
        return Response(serializer.data)

    def list(self, request, code):
        """获取模块的排序"""
        application = self.get_application()
        result = (
            ApplicationDeploymentModuleOrder.objects.filter(user=request.user.pk, module__application=application)
            .order_by("order")
            .values("order", module_name=F("module__name"))
        )
        serializer = slzs.ApplicationDeploymentModuleOrderSLZ(result, many=True)
        return Response(serializer.data)
