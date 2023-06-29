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
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, views, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.cluster.shim import get_application_cluster
from paasng.accessories.bk_lesscode.client import make_bk_lesscode_client
from paasng.accessories.bk_lesscode.exceptions import LessCodeApiError, LessCodeGatewayServiceError
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.constants import AccountFeatureFlag as AFF
from paasng.accounts.models import AccountFeatureFlag
from paasng.accounts.permissions.application import application_perm_class, check_application_perm
from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.models import Template
from paasng.engine.configurations.image import generate_image_repository
from paasng.engine.constants import RuntimeType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import application_default_module_switch, pre_delete_module
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.applications.utils import delete_module
from paasng.platform.modules.constants import DeployHookType, SourceOrigin
from paasng.platform.modules.exceptions import BPNotFound
from paasng.platform.modules.helpers import ModuleRuntimeBinder, ModuleRuntimeManager, get_image_labels_by_module
from paasng.platform.modules.manager import init_module_in_view
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner, BuildConfig, Module
from paasng.platform.modules.protections import ModuleDeletionPreparer
from paasng.platform.modules.serializers import (
    CreateCNativeModuleSLZ,
    CreateModuleSLZ,
    ListModulesSLZ,
    MinimalModuleSLZ,
    ModuleBuildConfigSLZ,
    ModuleDeployConfigSLZ,
    ModuleDeployHookSLZ,
    ModuleDeployProcfileSLZ,
    ModuleRuntimeBindSLZ,
    ModuleRuntimeOverviewSLZ,
    ModuleRuntimeSLZ,
    ModuleSLZ,
)
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.region.models import get_region
from paasng.publish.market.models import MarketConfig
from paasng.publish.market.protections import ModulePublishPreparer
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes
from paasng.utils.views import permission_classes as perm_classes

logger = logging.getLogger(__name__)


class ModuleViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    @transaction.atomic
    @swagger_auto_schema(request_body=CreateModuleSLZ, tags=["创建模块"])
    @perm_classes([application_perm_class(AppAction.MANAGE_MODULE)], policy='merge')
    def create(self, request, *args, **kwargs):
        """创建一个新模块, 创建 lesscode 模块时需要从cookie中获取用户登录信息,该 APIGW 不能直接注册到 APIGW 上提供"""
        application = self.get_application()
        self._ensure_allow_create_module(application)

        serializer = CreateModuleSLZ(data=request.data, context={'application': application})
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        source_init_template = data['source_init_template']
        tmpl = Template.objects.get(name=source_init_template, type=TemplateType.NORMAL)

        # Permission check for non-default source origin
        source_origin = SourceOrigin(data['source_origin'])
        self._ensure_source_origin_available(request.user, source_origin)

        # lesscode app needs to create an application on the bk_lesscode platform first
        if source_origin == SourceOrigin.BK_LESS_CODE:
            bk_token = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
            try:
                make_bk_lesscode_client(login_cookie=bk_token).create_app(
                    application.code, application.name, data['name']
                )
            except (LessCodeApiError, LessCodeGatewayServiceError) as e:
                raise error_codes.CREATE_LESSCODE_APP_ERROR.f(e.message)

        region = get_region(application.region)
        module = Module.objects.create(
            application=application,
            is_default=False,
            region=application.region,
            name=data['name'],
            language=tmpl.language,
            source_origin=data['source_origin'],
            source_init_template=source_init_template,
            owner=application.owner,
            creator=request.user.pk,
            exposed_url_type=region.entrance_config.exposed_url_type,
        )
        # Use the same cluster with previous modules
        cluster = get_application_cluster(application)

        ret = init_module_in_view(
            module,
            data['source_control_type'],
            data["source_repo_url"],
            data["source_repo_auth_info"],
            source_dir=data["source_dir"],
            cluster_name=cluster.name,
        )

        return Response(
            data={'module': ModuleSLZ(module).data, 'source_init_result': ret.source_init_result},
            status=status.HTTP_201_CREATED,
        )

    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def list(self, request, code):
        """查看所有应用模块"""
        slz = ListModulesSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        application = self.get_application()
        modules = application.modules.all().order_by('-is_default', 'name')

        # Filter modules by source_type
        if slz.data.get('source_origin'):
            modules = modules.filter(source_origin=slz.data['source_origin'])
        return Response(data=MinimalModuleSLZ(modules, many=True).data)

    @swagger_auto_schema(tags=['应用模块'], response_serializer=ModuleSLZ)
    @perm_classes([application_perm_class(AppAction.VIEW_BASIC_INFO)], policy='merge')
    def retrieve(self, request, code, module_name):
        """查看应用模块信息

        `web_config` 字段说明：

        - `templated_source_enabled`：模块使用是否了源码模板
        """
        application = self.get_application()
        module = application.get_module(module_name)
        return Response(data=ModuleSLZ(module).data, status=status.HTTP_200_OK)

    @perm_classes([application_perm_class(AppAction.MANAGE_MODULE)], policy='merge')
    def destroy(self, request, code, module_name):
        """
        删除蓝鲸应用模块

        - [测试地址](/api/bkapps/applications/{code}/modules/{module_name}/)
        """
        # TODO can create get_application func and refactor all the permissions logic in ApplicationViewset
        application = get_object_or_404(Application, code=code)
        check_application_perm(self.request.user, application, AppAction.DELETE_APPLICATION)

        if application.get_default_module().name == module_name:
            raise error_codes.CANNOT_DELETE_MODULE.f(_("主模块不允许被删除"))

        module = application.get_module(module_name)
        protection_status = ModuleDeletionPreparer(module).perform()
        if protection_status.activated:
            raise error_codes.CANNOT_DELETE_MODULE.f(protection_status.reason)

        # 审计记录在事务外创建, 避免由于数据库回滚而丢失
        pre_delete_module.send(sender=Module, module=module, operator=request.user.pk)
        try:
            delete_module(application, module_name, request.user.pk)
        except Exception as e:
            logger.exception(
                "unable to clean module<%s> of application<%s> related resources", module_name, application.code
            )
            raise error_codes.CANNOT_DELETE_MODULE.f(str(e))
        return Response(status=status.HTTP_204_NO_CONTENT)

    # [deprecated] use `api.applications.entrances.set_default_entrance` instead
    @transaction.atomic
    @perm_classes([application_perm_class(AppAction.MANAGE_MODULE)], policy='merge')
    def set_as_default(self, request, code, module_name):
        """设置某个模块为主模块"""
        application = self.get_application()
        default_module = application.get_default_module_with_lock()
        try:
            module = application.get_module_with_lock(module_name=module_name)
        except ObjectDoesNotExist:
            # 可能在设置之前模块已经被删除了
            raise error_codes.CANNOT_SET_DEFAULT.f(_("{module_name} 模块已经被删除").format(module_name=module_name))

        if module.name == default_module.name:
            raise error_codes.CANNOT_SET_DEFAULT.f(_("{module_name} 模块已经是主模块").format(module_name=module_name))

        try:
            market_enabled = application.market_config.enabled
        except MarketConfig.DoesNotExist:
            pass
        else:
            if market_enabled and not ModulePublishPreparer(module).all_matched:
                raise error_codes.CANNOT_SET_DEFAULT.f(
                    _("目标 {module_name} 模块未满足应用市场服务开启条件，切换主模块会导致应用在市场中访问异常").format(module_name=module_name)
                )

        logger.info(
            f'Switching default module for application[{application.code}], '
            f'{default_module.name} -> {module.name}...'
        )
        default_module.is_default = False
        module.is_default = True
        module.save(update_fields=["is_default", "updated"])
        default_module.save(update_fields=["is_default", "updated"])

        application_default_module_switch.send(
            sender=application, application=application, new_module=module, old_module=default_module
        )
        return Response(status=status.HTTP_200_OK)

    @transaction.atomic
    @perm_classes([application_perm_class(AppAction.MANAGE_MODULE)], policy='merge')
    def create_cloud_native_module(self, request, code):
        """创建云原生应用模块（非默认）"""
        application = self.get_application()
        self._ensure_allow_create_module(application)

        serializer = CreateCNativeModuleSLZ(data=request.data, context={'application': application})
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        src_cfg = data.get('source_config', {})
        # 检查当前用户能否使用指定的 source_origin
        self._ensure_source_origin_available(request.user, SourceOrigin(src_cfg['source_origin']))

        source_config = {'source_origin': src_cfg['source_origin']}
        if tmpl_name := src_cfg['source_init_template']:
            tmpl = Template.objects.get(name=tmpl_name, type=TemplateType.NORMAL)
            source_config.update({'language': tmpl.language, 'source_init_template': tmpl_name})

        module = Module.objects.create(
            application=application,
            is_default=False,
            region=application.region,
            name=data['name'],
            owner=application.owner,
            creator=request.user.pk,
            exposed_url_type=get_region(application.region).entrance_config.exposed_url_type,
            **source_config,
        )
        # 使用默认模块的 PROD 环境部署集群作为新模块集群
        cluster = get_application_cluster(application)

        build_cfg = data['build_config']
        build_config = BuildConfig.objects.get_or_create_by_module(module)
        try:
            build_config.update_with_build_method(
                build_cfg['build_method'],
                module,
                build_cfg.get('bp_stack_name'),
                build_cfg.get('buildpacks'),
                build_cfg.get('dockerfile_path'),
                build_cfg.get('docker_build_args'),
                build_cfg.get('tag_options'),
            )
        except BPNotFound:
            raise error_codes.BIND_RUNTIME_FAILED.f(_("构建工具不存在"))

        ret = init_module_in_view(
            module,
            repo_type=src_cfg.get('source_control_type'),
            repo_url=src_cfg.get('source_repo_url'),
            repo_auth_info=src_cfg.get('source_repo_auth_info'),
            source_dir=src_cfg.get('source_dir', ''),
            cluster_name=cluster.name,
            manifest=data.get('manifest'),
        )

        return Response(
            data={'module': ModuleSLZ(module).data, 'source_init_result': ret.source_init_result},
            status=status.HTTP_201_CREATED,
        )

    def _ensure_allow_create_module(self, application: Application):
        """检查当前应用是否允许继续创建模块"""
        if not AppSpecs(application).can_create_extra_modules:
            raise ValidationError(_("当前应用下不允许创建新模块"))

        modules_count = application.modules.count()
        if modules_count >= settings.MAX_MODULES_COUNT_PER_APPLICATION:
            raise error_codes.CREATE_MODULE_QUOTA_EXCEEDED.f(
                _("单个应用下最多能创建 {num} 个模块").format(num=settings.MAX_MODULES_COUNT_PER_APPLICATION)
            )

    def _ensure_source_origin_available(self, user, source_origin: SourceOrigin):
        """对使用非默认源码来源的，需要检查是否有权限"""
        if source_origin not in SourceOrigin.get_default_origins():
            if not AccountFeatureFlag.objects.has_feature(user, AFF.ALLOW_CHOOSE_SOURCE_ORIGIN):
                raise ValidationError(_('你无法使用非默认的源码来源'))


class ModuleRuntimeViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    # Deprecated: using ModuleBuildConfigViewSet
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list_available(self, request, code, module_name):
        """获取一个模块可用的运行环境"""
        application = self.get_application()
        module = application.get_module(module_name)

        results = []

        runtime_labels = get_image_labels_by_module(module)
        available_slugrunners = AppSlugRunner.objects.filter_by_label(module, runtime_labels)
        if available_slugrunners.count() == 0:
            available_slugrunners = AppSlugRunner.objects.filter_available(module)
        slugrunners = {i.name: i for i in available_slugrunners}

        available_slugbuilders = AppSlugBuilder.objects.filter_by_label(module, runtime_labels)
        if available_slugbuilders.count() == 0:
            available_slugbuilders = AppSlugBuilder.objects.filter_available(module)
        available_slugbuilders = available_slugbuilders.filter(name__in=slugrunners.keys())
        for slugbuilder in available_slugbuilders:
            name = slugbuilder.name
            results.append(
                {
                    "image": name,
                    "slugbuilder": slugbuilder,
                    "slugrunner": slugrunners.get(name),
                    "buildpacks": slugbuilder.get_buildpack_choices(module),
                }
            )

        return Response(data={"results": ModuleRuntimeSLZ(results, many=True).data})

    def retrieve(self, request, code, module_name):
        """获得当前绑定的运行时"""
        module = self.get_module_via_path()

        manager = ModuleRuntimeManager(module)
        slugbuilder = manager.get_slug_builder(raise_exception=False) or None
        slugrunner = manager.get_slug_runner(raise_exception=False) or None
        buildpacks = manager.list_buildpacks()

        slz = ModuleRuntimeSLZ(
            {
                "image": slugbuilder and slugbuilder.name,
                "slugbuilder": slugbuilder,
                "slugrunner": slugrunner,
                "buildpacks": buildpacks,
            }
        )

        # 强制转换成 dict 避免非 json 格式权限错误
        return Response(data=dict(slz.data))

    @transaction.atomic
    def bind(self, request, code, module_name):
        """解绑原有运行时，绑定新运行时"""
        application = self.get_application()
        module = application.get_module(module_name)

        slz = ModuleRuntimeBindSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        bp_stack_name = slz.validated_data["image"]
        buildpack_ids = slz.validated_data["buildpacks_id"]

        binder = ModuleRuntimeBinder(module)
        try:
            binder.bind_bp_stack(bp_stack_name, buildpack_ids)
        except BPNotFound:
            raise error_codes.BIND_RUNTIME_FAILED.f(_("构建工具不存在"))

        cfg = BuildConfig.objects.get_or_create_by_module(module)
        return Response(
            data={
                "image": bp_stack_name,
                "slugbuilder_id": cfg.buildpack_builder_id,
                "slugrunner_id": cfg.buildpack_runner_id,
                "buildpacks_id": buildpack_ids,
            }
        )


class ModuleRuntimeOverviewView(views.APIView, ApplicationCodeInPathMixin):
    # Deprecated: using ModuleBuildConfigViewSet
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(response_serializer=ModuleRuntimeOverviewSLZ)
    def get(self, request, code, module_name):
        """获取当前模块的运行时概览信息"""
        module = self.get_module_via_path()

        runtime_manager = ModuleRuntimeManager(module)
        slugbuilder = runtime_manager.get_slug_builder(raise_exception=False)
        buildpacks = runtime_manager.list_buildpacks()
        return Response(
            data=ModuleRuntimeOverviewSLZ(
                instance=dict(buildpacks=buildpacks, repo=module.get_source_obj(), language=module.language),
                context=dict(slugbuilder=slugbuilder, module=module, user=request.user),
            ).data
        )


class ModuleBuildConfigViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=ModuleBuildConfigSLZ)
    def retrieve(self, request, code, module_name):
        """获取当前模块的构建配置"""
        module = self.get_module_via_path()
        build_config = BuildConfig.objects.get_or_create_by_module(module)

        info = {
            "image_repository": generate_image_repository(module),
            "build_method": build_config.build_method,
            "tag_options": build_config.tag_options,
        }
        if build_config.build_method == RuntimeType.BUILDPACK:
            runtime_manager = ModuleRuntimeManager(module)
            slugbuilder = runtime_manager.get_slug_builder(raise_exception=False)
            buildpacks = runtime_manager.list_buildpacks()
            info.update(
                bp_stack_name=getattr(slugbuilder, "name", None),
                buildpacks=buildpacks,
            )
        else:
            info.update(
                dockerfile_path=build_config.dockerfile_path,
                docker_build_args=build_config.docker_build_args,
            )
        return Response(data=ModuleBuildConfigSLZ(info).data)

    @swagger_auto_schema(request_body=ModuleBuildConfigSLZ)
    def modify(self, request, code, module_name):
        """修改当前模块的构建配置"""
        slz = ModuleBuildConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module = self.get_module_via_path()
        build_config = BuildConfig.objects.get_or_create_by_module(module)

        build_method = data["build_method"]
        if build_method not in [RuntimeType.BUILDPACK, RuntimeType.DOCKERFILE]:
            raise error_codes.MODIFY_UNSUPPORTED.f(_("不支持的构建方式"))

        try:
            build_config.update_with_build_method(
                build_method,
                module,
                data.get('bp_stack_name'),
                data.get('buildpacks'),
                data.get('dockerfile_path'),
                data.get('docker_build_args'),
                data.get('tag_options'),
            )
        except BPNotFound:
            raise error_codes.BIND_RUNTIME_FAILED.f(_("构建工具不存在"))

        return Response()

    @swagger_auto_schema(response_serializer=ModuleRuntimeSLZ(many=True))
    def list_available_bp_runtimes(self, request, code, module_name):
        """获取一个模块可用的运行环境"""
        application = self.get_application()
        module = application.get_module(module_name)

        results = []
        runtime_labels = get_image_labels_by_module(module)
        available_slugrunners = AppSlugRunner.objects.filter_by_label(module, runtime_labels)
        if available_slugrunners.count() == 0:
            available_slugrunners = AppSlugRunner.objects.filter_available(module)
        slugrunners = {i.name: i for i in available_slugrunners}

        available_slugbuilders = AppSlugBuilder.objects.filter_by_label(module, runtime_labels)
        if available_slugbuilders.count() == 0:
            available_slugbuilders = AppSlugBuilder.objects.filter_available(module)
        available_slugbuilders = available_slugbuilders.filter(name__in=slugrunners.keys())
        for slugbuilder in available_slugbuilders:
            name = slugbuilder.name
            results.append(
                {
                    "image": name,
                    "slugbuilder": slugbuilder,
                    "slugrunner": slugrunners.get(name),
                    "buildpacks": slugbuilder.get_buildpack_choices(module),
                }
            )
        return Response(data=ModuleRuntimeSLZ(results, many=True).data)


class ModuleDeployConfigViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=ModuleDeployConfigSLZ)
    def retrieve(self, request, *args, **kwargs):
        """获取当前模块的部署配置信息"""
        module = self.get_module_via_path()
        deploy_config = module.get_deploy_config()

        return Response(ModuleDeployConfigSLZ(deploy_config).data)

    @swagger_auto_schema(request_body=ModuleDeployHookSLZ, responses={204: openapi_empty_response})
    def upsert_hook(self, request, *args, **kwargs):
        """更新或创建当前模块的部署配置的钩子"""
        module = self.get_module_via_path()
        deploy_config = module.get_deploy_config()

        slz = ModuleDeployHookSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        deploy_config.hooks.upsert(type_=data["type"], command=data["command"])
        deploy_config.save(update_fields=["hooks", "updated"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={204: openapi_empty_response})
    def disable_hook(self, request, code, module_name, type_: str):
        """禁用当前模块的部署配置的钩子"""
        module = self.get_module_via_path()
        deploy_config = module.get_deploy_config()

        try:
            deploy_config.hooks.disable(DeployHookType(type_))
            deploy_config.save(update_fields=["hooks", "updated"])
        except ValueError:
            raise ValidationError(detail={"type": f'“{type_}” 不是合法选项。'}, code="invalid_choice")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(request_body=ModuleDeployProcfileSLZ, response_serializer=ModuleDeployProcfileSLZ)
    def update_procfile(self, request, *args, **kwargs):
        """更新或创建当前模块的部署配置的启动命令"""
        module = self.get_module_via_path()
        if ModuleSpecs(module).runtime_type != RuntimeType.CUSTOM_IMAGE:
            raise ValidationError(_("当前应用不支持配置「启动命令」"))

        slz = ModuleDeployProcfileSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        deploy_config = module.get_deploy_config()
        deploy_config.procfile = data["procfile"]
        deploy_config.save(update_fields=["procfile", "updated"])

        return Response(ModuleDeployProcfileSLZ({"procfile": deploy_config.procfile}).data)
