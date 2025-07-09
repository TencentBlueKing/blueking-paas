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
from typing import Any, Dict

from bkpaas_auth.models import User
from django.conf import settings
from django.db import IntegrityError as DbIntegrityError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paas_wl.workloads.images.models import AppUserCredential
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.core.region.models import get_all_regions
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from paasng.infras.accounts.permissions.user import user_can_operate_in_region
from paasng.platform.applications.constants import AppEnvironment, ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.serializers import (
    AIAgentAppCreateInputSLZ,
    ApplicationCreateInputV2SLZ,
    ApplicationCreateOutputSLZ,
    CloudNativeAppCreateInputSLZ,
    CreationOptionsOutputSLZ,
    ThirdPartyAppCreateInputSLZ,
)
from paasng.platform.applications.signals import post_create_application
from paasng.platform.applications.tenant import validate_app_tenant_params
from paasng.platform.applications.utils import (
    create_application,
    create_default_module,
    create_market_config,
    create_third_app,
)
from paasng.platform.bk_lesscode.client import make_bk_lesscode_client
from paasng.platform.bk_lesscode.exceptions import LessCodeGatewayServiceError
from paasng.platform.modules.constants import ExposedURLType, ModuleName, SourceOrigin
from paasng.platform.modules.manager import create_new_repo, delete_repo_on_error, init_module_in_view
from paasng.platform.templates.models import Template
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ApplicationCreateViewSet(viewsets.ViewSet):
    serializer_class = None
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @swagger_auto_schema(
        tags=["platform.applications.creation"],
        operation_description="创建应用",
        request_body=ApplicationCreateInputV2SLZ,
        responses={status.HTTP_201_CREATED: ApplicationCreateOutputSLZ()},
    )
    def create_v2(self, request):
        slz = ApplicationCreateInputV2SLZ(data=request.data, context={"user": request.user})
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        self._validate_create_region_application_perm(params["region"])

        # 特殊处理，如果不启用应用引擎，则视为创建第三方应用
        if not params["engine_enabled"]:
            return self.create_third_party(request)

        engine_params = params.get("engine_params", {})
        source_origin = SourceOrigin(engine_params["source_origin"])

        # LessCode 应用需要调用 API 在 lesscode 平台创建应用
        if source_origin == SourceOrigin.BK_LESS_CODE:
            # 目前页面创建的应用名称都存储在 name_zh_cn 字段中, name_en 只用于 smart 应用
            self._create_app_on_lesscode_platform(request, params["code"], params["name_zh_cn"])

        env_cluster_names: Dict[str, str] = {}
        if advanced_options := params.get("advanced_options"):
            env_cluster_names = advanced_options.get("env_cluster_names", {})

        return self._init_application(request.user, params, engine_params, source_origin, env_cluster_names)

    @transaction.atomic
    @swagger_auto_schema(
        tags=["platform.applications.creation"],
        operation_description="创建云原生应用",
        request_body=CloudNativeAppCreateInputSLZ,
        responses={status.HTTP_201_CREATED: ApplicationCreateOutputSLZ()},
    )
    def create_cloud_native(self, request):
        slz = CloudNativeAppCreateInputSLZ(data=request.data, context={"user": request.user})
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        self._validate_create_region_application_perm(params["region"])

        src_cfg = params["source_config"]
        source_origin = SourceOrigin(src_cfg["source_origin"])
        module_src_cfg: Dict[str, Any] = {"source_origin": source_origin}

        # 如果指定模板信息，则需要提取并保存
        if tmpl_name := src_cfg["source_init_template"]:
            tmpl = Template.objects.get(name=tmpl_name)
            module_src_cfg.update({"language": tmpl.language, "source_init_template": tmpl_name})

        # LessCode 应用需要调用 API 在 LessCode 平台创建应用
        if source_origin == SourceOrigin.BK_LESS_CODE:
            # 目前页面创建的应用名称都存储在 name_zh_cn 字段中, name_en 只用于 smart 应用
            self._create_app_on_lesscode_platform(request, params["code"], params["name_zh_cn"])

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(
            request.user,
            params["app_tenant_mode"],
        )

        application = create_application(
            region=params["region"],
            code=params["code"],
            name=params["name_zh_cn"],
            name_en=params["name_en"],
            app_type=ApplicationType.CLOUD_NATIVE.value,
            operator=request.user.pk,
            is_plugin_app=params["is_plugin_app"],
            app_tenant_mode=app_tenant_mode,
            app_tenant_id=app_tenant_id,
            tenant_id=tenant.id,
        )
        module = create_default_module(application, **module_src_cfg)

        # 初始化应用镜像凭证信息
        if image_credential := params["bkapp_spec"]["build_config"].image_credential:
            try:
                AppUserCredential.objects.create(
                    application_id=application.id, tenant_id=application.tenant_id, **image_credential
                )
            except DbIntegrityError:
                raise error_codes.CREATE_CREDENTIALS_FAILED.f(_("同名凭证已存在"))

        env_cluster_names: Dict[str, str] = {}
        if advanced_options := params.get("advanced_options"):
            env_cluster_names = advanced_options.get("env_cluster_names", {})

        repo_type = src_cfg.get("source_control_type")
        repo_url = src_cfg.get("source_repo_url")
        # 由平台创建代码仓库
        auto_repo_url = None
        if src_cfg.get("auto_create_repo"):
            auto_repo_url = create_new_repo(module, repo_type, username=request.user.username)
            repo_url = auto_repo_url

        with delete_repo_on_error(repo_type, auto_repo_url):
            source_init_result = init_module_in_view(
                module,
                repo_type=repo_type,
                repo_url=repo_url,
                repo_auth_info=src_cfg.get("source_repo_auth_info"),
                source_dir=src_cfg.get("source_dir", ""),
                env_cluster_names=env_cluster_names,
                bkapp_spec=params["bkapp_spec"],
                write_template_to_repo=src_cfg.get("write_template_to_repo"),
            ).source_init_result

            post_create_application.send(sender=self.__class__, application=application)

            create_market_config(
                application=application,
                # 当应用开启引擎时, 则所有访问入口都与 Prod 一致
                source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
                # 对于新创建的应用, 如果生产环境集群支持 HTTPS, 则默认开启 HTTPS
                prefer_https=self._get_cluster_entrance_https_enabled(
                    application,
                    env_cluster_names.get(AppEnvironment.PRODUCTION),
                    ExposedURLType(module.exposed_url_type),
                ),
            )
        return Response(
            data=ApplicationCreateOutputSLZ(
                {"application": application, "source_init_result": source_init_result}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        tags=["platform.applications.creation"],
        operation_description="创建第三方（外链）应用",
        request_body=ThirdPartyAppCreateInputSLZ,
        responses={status.HTTP_201_CREATED: ApplicationCreateOutputSLZ()},
    )
    def create_third_party(self, request):
        slz = ThirdPartyAppCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        self._validate_create_region_application_perm(data["region"])

        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(
            request.user,
            data["app_tenant_mode"],
        )
        application = create_third_app(
            data["region"],
            data["code"],
            data["name_zh_cn"],
            data["name_en"],
            request.user.pk,
            app_tenant_mode,
            app_tenant_id,
            tenant.id,
            data["market_params"],
        )

        return Response(
            data=ApplicationCreateOutputSLZ({"application": application, "source_init_result": None}).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    @swagger_auto_schema(
        tags=["platform.applications.creation"],
        operation_description="创建 LessCode（蓝鲸可视化开发平台）应用",
        request_body=ApplicationCreateInputV2SLZ,
        responses={status.HTTP_201_CREATED: ApplicationCreateOutputSLZ()},
    )
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
        slz = ApplicationCreateInputV2SLZ(data=request.data, context={"user": request.user})
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        self._validate_create_region_application_perm(params["region"])

        engine_params = params.get("engine_params", {})
        source_origin = SourceOrigin(engine_params["source_origin"])
        # LessCode 应用不支持指定集群，只能使用默认集群
        env_cluster_names: Dict[str, str] = {}

        return self._init_application(request.user, params, engine_params, source_origin, env_cluster_names)

    @transaction.atomic
    @swagger_auto_schema(
        tags=["platform.applications.creation"],
        operation_description="创建 AI Agent 插件应用",
        request_body=AIAgentAppCreateInputSLZ,
        responses={status.HTTP_201_CREATED: ApplicationCreateOutputSLZ()},
    )
    def create_ai_agent_app(self, request):
        serializer = AIAgentAppCreateInputSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        self._validate_create_region_application_perm(params["region"])

        source_origin = SourceOrigin.AI_AGENT
        engine_params = {
            "source_origin": source_origin,
            # TODO AI agent 还没有提供模板，目前是直接使用 Python 插件的模板
            "source_init_template": "bk-saas-plugin-python",
        }
        # ai-agent-app 不支持指定集群（使用默认集群）
        env_cluster_names: Dict[str, str] = {}

        return self._init_application(request.user, params, engine_params, source_origin, env_cluster_names)

    @swagger_auto_schema(
        tags=["platform.applications.creation"],
        operation_description="获取创建应用高级选项",
        responses={status.HTTP_201_CREATED: CreationOptionsOutputSLZ()},
    )
    def get_creation_options(self, request):
        """[API] 获取创建应用模块时的高级选项配置"""
        # 是否允许用户使用高级选项
        allow_advanced = AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_ADVANCED_CREATION_OPTIONS)

        adv_region_clusters = []
        for region_name in get_all_regions():
            env_cluster_names = {}
            for env in [AppEnvironment.STAGING, AppEnvironment.PRODUCTION]:
                ctx = AllocationContext(
                    tenant_id=get_tenant(request.user).id,
                    region=region_name,
                    environment=env,
                    username=request.user.username,
                )
                env_cluster_names[env] = [cluster.name for cluster in ClusterAllocator(ctx).list()]

            adv_region_clusters.append({"region": region_name, "env_cluster_names": env_cluster_names})

        resp_data = {"allow_adv_options": allow_advanced, "adv_region_clusters": adv_region_clusters}
        return Response(CreationOptionsOutputSLZ(resp_data).data)

    def _validate_create_region_application_perm(self, region: str):
        if not user_can_operate_in_region(self.request.user, region):
            raise error_codes.CANNOT_CREATE_APP.f(_("无法在所指定的 region 中创建应用"))

    def _get_cluster_entrance_https_enabled(
        self, app: Application, cluster_name: str | None, exposed_url_type: ExposedURLType
    ) -> bool:
        ctx = AllocationContext(
            tenant_id=app.tenant_id,
            region=app.region,
            # 注：这里用途是创建市场配置，因此固定为生产环境
            environment=AppEnvironment.PRODUCTION,
            username=self.request.user.username,
        )
        cluster = ClusterAllocator(ctx).get(cluster_name)

        try:
            if exposed_url_type == ExposedURLType.SUBDOMAIN:
                return cluster.ingress_config.default_root_domain.https_enabled
            else:
                return cluster.ingress_config.default_sub_path_domain.https_enabled
        except IndexError:
            # exposed_url_type == SUBDOMAIN 的集群, 应当配置 default_root_domain
            # exposed_url_type == SUBPATH 的集群, 应当配置 default_sub_path_domain
            logger.warning(_("集群未配置默认的根域名, 请检查集群配置是否合理."))
            return False

    def _create_app_on_lesscode_platform(self, request, code: str, name: str):
        """在开发者中心产品页面上创建 Lesscode 应用时，需要同步在 Lesscode 平台上创建应用"""
        login_cookie = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
        try:
            client = make_bk_lesscode_client(login_cookie=login_cookie, tenant_id=get_tenant(request.user).id)
            client.create_app(code, name, ModuleName.DEFAULT.value)
        except LessCodeGatewayServiceError as e:
            raise error_codes.CREATE_LESSCODE_APP_ERROR.f(e.message)

    def _init_application(
        self,
        request_user: User,
        params: Dict,
        engine_params: Dict,
        source_origin: SourceOrigin,
        env_cluster_names: Dict[str, str],
    ) -> Response:
        """初始化应用，包含创建默认模块，应用市场配置等"""
        app_tenant_mode, app_tenant_id, tenant = validate_app_tenant_params(
            request_user,
            params["app_tenant_mode"],
        )

        application = create_application(
            region=params["region"],
            code=params["code"],
            name=params["name_zh_cn"],
            name_en=params["name_en"],
            app_type=params["type"],
            is_plugin_app=params["is_plugin_app"],
            is_ai_agent_app=params["is_ai_agent_app"],
            operator=request_user.pk,
            app_tenant_mode=app_tenant_mode,
            app_tenant_id=app_tenant_id,
            tenant_id=tenant.id,
        )

        # Create engine related data
        # `source_init_template` is optional
        source_init_template = engine_params.get("source_init_template", "")
        language = ""
        if source_init_template:
            language = Template.objects.get(name=source_init_template).language

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
            env_cluster_names=env_cluster_names,
        ).source_init_result

        if language:
            application.language = language
            application.save(update_fields=["language"])

        post_create_application.send(sender=self.__class__, application=application)

        create_market_config(
            application=application,
            # 当应用开启引擎时, 则所有访问入口都与 Prod 一致
            source_url_type=ProductSourceUrlType.ENGINE_PROD_ENV,
            # 对于新创建的应用, 如果生产环境集群支持 HTTPS, 则默认开启 HTTPS
            prefer_https=self._get_cluster_entrance_https_enabled(
                application,
                env_cluster_names.get(AppEnvironment.PRODUCTION),
                ExposedURLType(module.exposed_url_type),
            ),
        )

        return Response(
            data=ApplicationCreateOutputSLZ(
                {"application": application, "source_init_result": source_init_result}
            ).data,
            status=status.HTTP_201_CREATED,
        )
