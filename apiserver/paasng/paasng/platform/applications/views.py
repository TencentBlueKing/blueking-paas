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
import base64
import logging
import random
import string
from collections import Counter, defaultdict
from io import BytesIO
from operator import itemgetter
from typing import Any, Dict, Iterable, Optional

import cattr
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.accessories.bk_lesscode.client import make_bk_lesscode_client
from paasng.accessories.bk_lesscode.exceptions import LessCodeApiError, LessCodeGatewayServiceError
from paasng.accessories.iam.helpers import (
    add_role_members,
    fetch_application_members,
    fetch_role_members,
    fetch_user_main_role,
    remove_user_all_roles,
)
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.constants import AccountFeatureFlag as AFF
from paasng.accounts.constants import FunctionType
from paasng.accounts.models import AccountFeatureFlag, make_verifier
from paasng.accounts.permissions.application import application_perm_class, check_application_perm
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_required
from paasng.accounts.serializers import VerificationCodeSLZ
from paasng.cnative import initialize_simple
from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.models import Template
from paasng.engine.controller.cluster import get_engine_app_cluster, get_region_cluster_helper
from paasng.extensions.bk_plugins.config import get_bk_plugin_config
from paasng.extensions.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.extensions.scene_app.initializer import SceneAPPInitializer
from paasng.platform.applications import serializers as slzs
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
    ApplicationEnvironment,
    UserApplicationFilter,
    UserMarkedApplication,
)
from paasng.platform.applications.protections import AppResProtector, ProtectedRes, raise_if_protected
from paasng.platform.applications.serializers import ApplicationMemberRoleOnlySLZ, ApplicationMemberSLZ
from paasng.platform.applications.signals import (
    application_member_updated,
    post_create_application,
    pre_delete_application,
)
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.applications.tasks import sync_developers_to_sentry
from paasng.platform.applications.utils import (
    create_application,
    create_default_module,
    create_market_config,
    create_third_app,
    delete_all_modules,
)
from paasng.platform.core.storages.s3 import app_logo_storage
from paasng.platform.core.storages.sqlalchemy import legacy_db
from paasng.platform.feature_flags.constants import PlatformFeatureFlag
from paasng.platform.mgrlegacy.constants import LegacyAppState
from paasng.platform.modules.constants import ExposedURLType, ModuleName, SourceOrigin
from paasng.platform.modules.manager import init_module_in_view
from paasng.platform.modules.protections import ConditionNotMatched, ModuleDeletionPreparer
from paasng.platform.oauth2.utils import get_oauth2_client_secret
from paasng.platform.region.models import get_all_regions
from paasng.platform.region.permissions import HasPostRegionPermission
from paasng.publish.market.constant import AppState, ProductSourceUrlType
from paasng.publish.market.models import MarketConfig, Product
from paasng.publish.sync_market.managers import AppDeveloperManger
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.error_codes import error_codes
from paasng.utils.error_message import wrap_validation_error
from paasng.utils.views import permission_classes as perm_classes

try:
    from paasng.platform.legacydb_te.adaptors import AppAdaptor, AppTagAdaptor
    from paasng.platform.legacydb_te.models import get_developers_by_v2_application
except ImportError:
    from paasng.platform.legacydb.adaptors import AppAdaptor, AppTagAdaptor  # type: ignore
    from paasng.platform.legacydb.models import get_developers_by_v2_application  # type: ignore

logger = logging.getLogger(__name__)


class ApplicationViewSet(viewsets.ViewSet):
    """View class for applications"""

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import LimitOffsetPagination

            self._paginator = LimitOffsetPagination()
            self._paginator.default_limit = 12
        return self._paginator

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
            exclude_collaborated=params.get('exclude_collaborated'),
            include_inactive=params['include_inactive'],
            languages=params.get('language'),
            regions=params.get('region'),
            search_term=params.get('search_term'),
            source_origin=params.get('source_origin'),
            type_=params.get('type'),
            order_by=[params.get('order_by')],
        )

        # 如果将用户标记的应用排在前面，需要特殊处理一下
        if params.get('prefer_marked'):
            applications_ids = applications.values_list('id', flat=True)
            applications_ids = sorted(applications_ids, key=lambda x: x in marked_application_ids, reverse=True)

            # Paginator
            page = self.paginator.paginate_queryset(applications_ids, self.request, view=self)
            page_applications = list(Application.objects.filter(id__in=page).select_related('product'))
            page_applications = sorted(page_applications, key=lambda x: applications_ids.index(x.id))
        else:
            page_applications = self.paginator.paginate_queryset(applications, self.request, view=self)

        data = [
            {
                'application': application,
                'product': application.product if hasattr(application, "product") else None,
                'marked': application.id in marked_application_ids,
            }
            for application in page_applications
        ]

        serializer = slzs.ApplicationWithMarketSLZ(data, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(query_serializer=slzs.ApplicationListMinimalSLZ)
    def list_minimal(self, request):
        """[API] 查询简单应用列表"""
        # Get applications by given params
        serializer = slzs.ApplicationListMinimalSLZ(data=request.query_params)
        serializer.is_valid()
        params = serializer.data

        applications = UserApplicationFilter(request.user).filter(
            order_by=['code'],
            include_inactive=params["include_inactive"],
            source_origin=params.get("source_origin", None),
        )
        results = [
            {'application': application, 'product': application.product if hasattr(application, "product") else None}
            for application in applications
        ]
        serializer = slzs.ApplicationWithMarketMinimalSLZ(results, many=True)
        return Response({'count': len(results), 'results': serializer.data})

    def get_cluster_by_app(self, application: Application):
        for env in application.envs.all():
            cluster = get_engine_app_cluster(application.region, env.engine_app.name)
            if cluster:
                return cluster

    def retrieve(self, request, code):
        """获取单个应用的信息"""
        application = get_object_or_404(Application, code=code)
        check_application_perm(request.user, application, AppAction.VIEW_BASIC_INFO)

        main_role = fetch_user_main_role(code, request.user.username)
        product = application.get_product()

        web_config = application.config_info
        cluster = self.get_cluster_by_app(application)
        # We may not reuse this structure, so I will not make it a serializer
        return Response(
            {
                'role': slzs.RoleField().to_representation(main_role),
                'application': slzs.ApplicationSLZ(application).data,
                'product': slzs.ProductSLZ(product).data if product else None,
                'marked': UserMarkedApplication.objects.filter(
                    application=application, owner=request.user.pk
                ).exists(),
                'web_config': web_config,
                'cluster': cattr.unstructure(cluster) if cluster else None,
            }
        )

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
            return Response({'count': 0, 'results': []})

        params = serializer.data
        keyword = params.get('keyword')
        # Get applications which contains keywords
        applications = UserApplicationFilter(request.user).filter(
            include_inactive=params['include_inactive'], order_by=['code', 'name'], search_term=keyword
        )

        if params.get("prefer_marked"):
            # get marked application ids
            marked_applications = UserMarkedApplication.objects.filter(owner=request.user.pk)
            marked_application_ids = set(marked_applications.values_list("application__id", flat=True))
            # then sort it
            applications = sorted(applications, key=lambda app: app.id in marked_application_ids, reverse=True)

        serializer = slzs.AppMinimalWithModuleSLZ(applications, many=True)
        return Response({'count': len(applications), 'results': serializer.data})

    def destroy(self, request, code):
        """
        删除蓝鲸应用

        - [测试地址](/api/bkapps/applications/{code}/)
        """
        # TODO can create get_application func and refactor all the permissions logic in ApplicationViewset
        application = get_object_or_404(Application, code=code)
        check_application_perm(self.request.user, application, AppAction.DELETE_APPLICATION)

        market_config, _created = MarketConfig.objects.get_or_create_by_app(application)
        if market_config.enabled:
            raise error_codes.CANNOT_DELETE_APP.f(_("删除应用前, 请先从到「应用市场」下架该应用"))

        modules = application.modules.all()
        for module in modules:
            try:
                ModuleDeletionPreparer(module).perform()
            except ConditionNotMatched as e:
                raise error_codes.CANNOT_DELETE_APP.f(e.message)

        # 审计记录在事务外创建, 避免由于数据库回滚而丢失
        pre_delete_application.send(sender=Application, application=application, operator=self.request.user.pk)
        with transaction.atomic():
            self._delete_all_module(application)
            self._delete_application(application)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _delete_all_module(self, application: Application):
        try:
            delete_all_modules(application, self.request.user.pk)
        except Exception as e:
            logger.exception("unable to clean application related resources")
            raise error_codes.CANNOT_DELETE_APP.f(str(e))

    def _delete_application(self, application: Application):
        try:
            application.delete()
        except Exception as e:
            logger.exception(f"unable to delete application {application.code}")
            raise error_codes.CANNOT_DELETE_APP.f(str(e))

    @transaction.atomic
    def update(self, request, code):
        """
        更新蓝鲸应用基本信息（应用名称）
        - [测试地址](/api/bkapps/applications/{code}/)
        - param: name, 应用名称
        """
        application = get_object_or_404(Application, code=code)
        # 编辑应用名称的权限：管理员、运营
        check_application_perm(self.request.user, application, AppAction.EDIT_BASIC_INFO)
        # Check if app was protected
        raise_if_protected(application, ProtectedRes.BASIC_INFO_MODIFICATIONS)

        serializer = slzs.UpdateApplicationSLZ(data=request.data, instance=application)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        Product.objects.filter(code=code).update(name_zh_cn=application.name, name_en=application.name_en)
        return Response(serializer.data)

    def check_manage_permissions(self, request, application):
        check_application_perm(request.user, application, AppAction.BASIC_DEVELOP)


class ApplicationCreateViewSet(viewsets.ViewSet):
    serializer_class = None
    permission_classes = [IsAuthenticated, HasPostRegionPermission]

    @swagger_auto_schema(request_body=slzs.CreateThirdPartyApplicationSLZ, tags=["创建应用"])
    def create_third_party(self, request):
        """[API] 创建第三方应用(外链应用)"""
        serializer = slzs.CreateThirdPartyApplicationSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        market_params = data['market_params']
        operator = request.user.pk

        if data["engine_enabled"]:
            raise ValidationError("该接口只支持创建外链应用")

        application = create_third_app(
            data['region'], data["code"], data["name_zh_cn"], data["name_en"], operator, market_params
        )

        return Response(
            data={'application': slzs.ApplicationSLZ(application).data, 'source_init_result': None},
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
        engine_params = params.get('engine_params', {})

        if not params["engine_enabled"]:
            return self.create_third_party(request)

        # Handle advanced options
        advanced_options = params.get('advanced_options', {})
        cluster_name = None
        if advanced_options:
            # Permission check
            if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS):
                raise ValidationError(_('你无法使用高级创建选项'))

            cluster_name = advanced_options.get('cluster_name')

        # Permission check for non-default source origin
        source_origin = SourceOrigin(engine_params['source_origin'])
        if source_origin not in SourceOrigin.get_default_origins():
            if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN):
                raise ValidationError(_('你无法使用非默认的源码来源'))

        # Guide: check if a bk_plugin can be created
        if params['type'] == ApplicationType.BK_PLUGIN and not get_bk_plugin_config(params['region']).allow_creation:
            raise ValidationError(_('当前版本下无法创建蓝鲸插件应用'))

        if source_origin == SourceOrigin.SCENE:
            return self._init_scene_app(request, params, engine_params)

        # lesscode app needs to create an application on the bk_lesscode platform first
        bk_token = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
        if source_origin == SourceOrigin.BK_LESS_CODE:
            try:
                # 目前页面创建的应用名称都存储在 name_zh_cn 字段中, name_en 只用于 smart 应用
                make_bk_lesscode_client(login_cookie=bk_token).create_app(
                    params["code"], params["name_zh_cn"], ModuleName.DEFAULT.value
                )
            except (LessCodeApiError, LessCodeGatewayServiceError) as e:
                raise error_codes.CREATE_LESSCODE_APP_ERROR.f(e.message)

        return self._init_normal_app(params, engine_params, source_origin, cluster_name, request.user.pk)

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
        serializer = slzs.CreateApplicationV2SLZ(data=request.data, context={"region": request.data["region"]})
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        engine_params = params.get('engine_params', {})

        # Permission check for non-default source origin
        source_origin = SourceOrigin(engine_params['source_origin'])
        if source_origin not in SourceOrigin.get_default_origins():
            if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN):
                raise ValidationError(_('你无法使用非默认的源码来源'))

        cluster_name = None
        return self._init_normal_app(params, engine_params, source_origin, cluster_name, request.user.pk)

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateCloudNativeAppSLZ, tags=["创建应用"])
    def create_cloud_native(self, request):
        """[API] 创建云原生架构应用

        `cloud_native_params` 为 object 类型，各字段说明：

        - `image`: string | 必填 | 容器镜像地址，
        - `command`：array[string] | 选填 | 启动命令列表，例如 ["/bin/bash"]
        - `args`：array[string] | 选填 | 命令参数列表，例如 ["-name", "demo"]
        - `target_port`：integer | 选填 | 容器端口
        """
        if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_CREATE_CLOUD_NATIVE_APP):
            raise ValidationError(_('你无法创建云原生应用'))

        serializer = slzs.CreateCloudNativeAppSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.data

        advanced_options = params.get('advanced_options', {})
        cluster_name = None
        if advanced_options:
            if not AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS):
                raise ValidationError(_('你无法使用高级创建选项'))
            cluster_name = advanced_options.get('cluster_name')

        application = create_application(
            region=params["region"],
            code=params["code"],
            name=params["name_zh_cn"],
            name_en=params["name_en"],
            type_=ApplicationType.CLOUD_NATIVE.value,
            operator=request.user.pk,
        )
        create_default_module(application)

        # Initialize by calling "workloads" service
        try:
            initialize_simple(application.default_module, params['cloud_native_params'], cluster_name)
        except ValidationError as exc:
            raise wrap_validation_error(exc, parent='cloud_native_params')

        post_create_application.send(sender=self.__class__, application=application)
        create_market_config(
            application=application,
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
        )
        return Response(
            data={'application': slzs.ApplicationSLZ(application).data, 'source_init_result': None},
            status=status.HTTP_201_CREATED,
        )

    def get_creation_options(self, request):
        """[API] 获取创建应用模块时的选项信息"""
        # 是否允许用户使用高级选项
        allow_advanced = AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS)
        adv_region_clusters = []
        if allow_advanced:
            for name in get_all_regions().keys():
                clusters = get_region_cluster_helper(name).list_clusters()
                adv_region_clusters.append({'region': name, 'cluster_names': [cluster.name for cluster in clusters]})

        options = {
            # configs related with "bk_plugin"
            'bk_plugin_configs': list(self._get_bk_plugin_configs()),
            # ADVANCED options:
            'allow_adv_options': allow_advanced,
            # configs related with clusters, contains content only when "allow_adv_options" is true
            'adv_region_clusters': adv_region_clusters,
        }
        return Response(options)

    def _get_bk_plugin_configs(self) -> Iterable[Dict]:
        """Get configs for bk_plugin module"""
        for name in get_all_regions().keys():
            yield {'region': name, 'allow_creation': get_bk_plugin_config(name).allow_creation}

    def _get_cluster_entrance_https_enabled(
        self, region: str, cluster_name: Optional[str], exposed_url_type: ExposedURLType
    ) -> bool:
        if not cluster_name:
            cluster = get_region_cluster_helper(region).get_default_cluster()
        else:
            cluster = get_region_cluster_helper(region).get_cluster(cluster_name)

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
    ) -> Response:
        """初始化普通应用，包含创建默认模块，应用市场配置等"""
        application = create_application(
            region=params["region"],
            code=params["code"],
            name=params["name_zh_cn"],
            name_en=params["name_en"],
            type_=params["type"],
            operator=operator,
        )

        app_specs = AppSpecs(application)
        language = app_specs.language_by_default

        # Create engine related data
        # `source_init_template` is optional
        source_init_template = engine_params.get('source_init_template', '')
        if source_init_template:
            language = Template.objects.get(name=source_init_template, type=TemplateType.NORMAL).language

        module = create_default_module(
            application,
            source_init_template=source_init_template,
            language=language,
            source_origin=source_origin,
        )
        source_init_result = init_module_in_view(
            module,
            repo_type=engine_params.get('source_control_type'),
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
            application.save(update_fields=['language'])

        post_create_application.send(sender=self.__class__, application=application)
        create_market_config(
            application=application,
            # 当应用开启引擎时, 则所有访问入口都与 Prod 一致
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
            # 对于新创建的应用, 如果集群支持 HTTPS, 则默认开启 HTTPS
            prefer_https=https_enabled,
        )

        return Response(
            data={'application': slzs.ApplicationSLZ(application).data, 'source_init_result': source_init_result},
            status=status.HTTP_201_CREATED,
        )

    def _init_scene_app(self, request, params: Dict, engine_params: Dict) -> Response:
        """初始化场景 SaaS 应用，包含根据 app_desc 文件创建一或多个模块，配置应用市场配置等"""
        tmpl_name = engine_params.get('source_init_template', '')
        app_name, app_code, region = params['name_en'], params['code'], params['region']

        try:
            application, result = SceneAPPInitializer(
                request.user, tmpl_name, app_name, app_code, region, engine_params
            ).execute()
        except DescriptionValidationError as e:
            logger.exception("Invalid app_desc.yaml cause create app failed")
            raise error_codes.SCENE_TMPL_DESC_ERROR.f(e.message)
        except ControllerError as e:
            logger.exception("Controller error cause create app failed")
            raise error_codes.CANNOT_CREATE_APP.f(e.message)

        source_init_result: Dict[str, Any] = {'code': result.error}
        if result.is_success():
            source_init_result = {'code': 'OK', 'extra_info': result.extra_info, 'dest_type': result.dest_type}

        return Response(
            data={
                'application': slzs.ApplicationSLZ(application).data,
                'source_init_result': source_init_result,
            },
            status=status.HTTP_201_CREATED,
        )


class ApplicationMembersViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """Viewset for application members management"""

    pagination_class = None
    permission_classes = [IsAuthenticated]

    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def list(self, request, **kwargs):
        """Always add 'result' key in response"""
        members = fetch_application_members(self.get_application().code)
        return Response({'results': ApplicationMemberSLZ(members, many=True).data})

    @perm_classes([application_perm_class(AppAction.MANAGE_MEMBERS)], policy='merge')
    def create(self, request, **kwargs):
        application = self.get_application()

        serializer = ApplicationMemberSLZ(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        role_members_map = defaultdict(list)
        for info in serializer.data:
            for role in info['roles']:
                role_members_map[role['id']].append(info['user']['username'])

        for role, members in role_members_map.items():
            add_role_members(application.code, role, members)

        application_member_updated.send(sender=application, application=application)
        sync_developers_to_sentry.delay(application.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @perm_classes([application_perm_class(AppAction.MANAGE_MEMBERS)], policy='merge')
    def update(self, request, *args, **kwargs):
        application = self.get_application()

        serializer = ApplicationMemberRoleOnlySLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = get_username_by_bkpaas_user_id(kwargs['user_id'])
        self.check_admin_count(application.code, username)
        remove_user_all_roles(application.code, username)
        add_role_members(application.code, ApplicationRole(serializer.data['role']['id']), username)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def leave(self, request, *args, **kwargs):
        application = self.get_application()
        user = request.user
        if application.owner == user.pk:  # owner can not leave application
            raise error_codes.MEMBERSHIP_OWNER_FAILED

        self.check_admin_count(application.code, request.user.username)
        remove_user_all_roles(application.code, request.user.username)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @perm_classes([application_perm_class(AppAction.MANAGE_MEMBERS)], policy='merge')
    def destroy(self, request, *args, **kwargs):
        application = self.get_application()

        username = get_username_by_bkpaas_user_id(kwargs['user_id'])
        self.check_admin_count(application.code, username)
        remove_user_all_roles(application.code, username)

        sync_developers_to_sentry.delay(application.id)
        application_member_updated.send(sender=application, application=application)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def check_admin_count(self, app_code: str, username: str):
        # Check whether the application has at least one administrator when the membership was deleted
        administrators = fetch_role_members(app_code, ApplicationRole.ADMINISTRATOR)
        if len(administrators) <= 1 and username in administrators:
            raise error_codes.MEMBERSHIP_DELETE_FAILED

    def get_roles(self, request):
        return Response({'results': ApplicationRole.get_django_choices()})


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
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' % (self.__class__.__name__, lookup_url_kwarg)
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
        never_deployed = queryset.filter(deployments__isnull=True, environment='stag').values('id').distinct().count()

        # 预发布环境的应用, 需要排除同时部署过预发布环境和正式环境的应用
        prod_deployed_ids = queryset.filter(is_offlined=False, deployments__isnull=False, environment='prod').values(
            'id'
        )
        stag_deployed = (
            queryset.filter(is_offlined=False, deployments__isnull=False, environment='stag')
            .exclude(id__in=prod_deployed_ids)
            .values('id')
            .distinct()
            .count()
        )

        prod_deployed = (
            queryset.filter(is_offlined=False, deployments__isnull=False, environment='prod')
            .values('id')
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
        include_inactive = params['include_inactive']
        group_field = params['field']

        queryset = Application.objects.filter_by_user(request.user)
        # 从用户角度来看，应用分类需要区分是否为已删除应用
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        application_group = queryset.values_list(group_field, flat=True)
        counter: Dict[str, int] = Counter(application_group)
        groups = [{group_field: group, "count": count} for group, count in list(counter.items())]
        # sort by count
        sorted_groups = sorted(groups, key=itemgetter('count'), reverse=True)
        data = {"total": queryset.count(), "groups": sorted_groups}
        return Response(data)


class ApplicationExtraInfoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_secret(self, request, code):
        """获取单个应用的secret"""
        application = self.get_application()

        if PlatformFeatureFlag.get_default_flags()[PlatformFeatureFlag.VERIFICATION_CODE]:
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

        client_secret = get_oauth2_client_secret(application.code, application.region)
        return Response({"app_code": application.code, "app_secret": client_secret})


class ApplicationFeatureFlagViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    @swagger_auto_schema(tags=["特性标记"])
    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def list(self, request, code):
        application = self.get_application()
        return Response(application.feature_flag.get_application_features())

    @swagger_auto_schema(tags=["特性标记"])
    @perm_classes([application_perm_class(AppAction.BASIC_DEVELOP)], policy='merge')
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
                logo_url = ''

            try:
                light_app = AppAdaptor(session=session).create(
                    code=app_code,
                    name=data["name"],
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
                logger.exception("save app base info fail: %s", e)
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
            except Exception as e:
                logger.exception(u"save app base info fail: %s", e)
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
            except Exception as e:
                logger.exception("save app base info fail: %s", e)
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
        ALPHABET = string.digits + string.ascii_lowercase

        # 轻应用的 app code 根据约定长度为 15
        # 为保证可创建的轻应用足够多(至少 36 * 36 个), 至少保留 2 位由随机字符生成
        parent_code = parent_code[:13]
        salt = ''.join(random.choices(ALPHABET, k=15 - len(parent_code)))

        return f"{parent_code}_{salt}"

    @classmethod
    def get_available_light_app_code(cls, session, parent_code, max_times=10):
        app_manager = AppAdaptor(session=session)
        for i in range(max_times):
            app_code = cls.generate_app_maker_code(parent_code)
            if not app_manager.get(app_code):
                return app_code

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

            initialize_app_logo_metadata(Application._meta.get_field('logo').storage, bucket, logo_name)
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

    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def retrieve(self, request, code):
        """查看应用 Logo 相关信息"""
        serializer = slzs.ApplicationLogoSLZ(instance=self.get_application())
        return Response(serializer.data)

    @perm_classes([application_perm_class(AppAction.EDIT_BASIC_INFO)], policy='merge')
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

        operator = user_id_encoder.encode(settings.USER_TYPE, data['operator'])

        application = create_third_app(data['region'], data["code"], data["name_zh_cn"], data["name_en"], operator)

        # 返回应用的密钥信息
        secret = get_oauth2_client_secret(application.code, application.region)
        return Response(
            data={"bk_app_code": application.code, "bk_app_secret": secret},
            status=status.HTTP_201_CREATED,
        )
