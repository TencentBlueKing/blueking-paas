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

"""应用创建（普通/云原生/外链等）API"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import IntegrityError as DbIntegrityError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.shim import RegionClusterService
from paas_wl.workloads.images.models import AppUserCredential
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.core.region.models import get_all_regions
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, get_tenant
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.infras.accounts.permissions.user import user_can_create_in_region
from paasng.platform.applications import serializers as slzs
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import post_create_application
from paasng.platform.applications.tenant import validate_app_tenant_params
from paasng.platform.applications.utils import (
    create_application,
    create_default_module,
    create_market_config,
    create_third_app,
)
from paasng.platform.bk_lesscode.client import make_bk_lesscode_client
from paasng.platform.bk_lesscode.exceptions import LessCodeApiError, LessCodeGatewayServiceError
from paasng.platform.declarative.exceptions import ControllerError, DescriptionValidationError
from paasng.platform.modules.constants import ExposedURLType, ModuleName, SourceOrigin
from paasng.platform.modules.manager import init_module_in_view
from paasng.platform.scene_app.initializer import SceneAPPInitializer
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


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
        """[API] 获取创建应用模块时的选项信息

        [deprecated] 该 API 将被废弃，通过其他 API 向前端提供用户可选的集群
        """
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
