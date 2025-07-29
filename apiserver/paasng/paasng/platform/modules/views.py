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
from typing import Any, Dict

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError as DbIntegrityError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, views, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.shim import get_app_cluster_names
from paas_wl.workloads.images.models import AppUserCredential
from paasng.accessories.publish.market.models import MarketConfig
from paasng.accessories.publish.market.protections import ModulePublishPreparer
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.application import (
    app_view_actions_perm,
    application_perm_class,
    check_application_perm,
)
from paasng.infras.accounts.permissions.user import user_can_operate_in_region
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.platform.applications.serializers.creation import SourceInitResultSLZ
from paasng.platform.applications.signals import application_default_module_switch
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.bk_lesscode.client import make_bk_lesscode_client
from paasng.platform.bk_lesscode.exceptions import LessCodeApiError, LessCodeGatewayServiceError
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import Process
from paasng.platform.bkapp_model.entities_syncer import sync_processes
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.configurations.image import generate_image_repositories_by_module
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.constants import DeployHookType, SourceOrigin
from paasng.platform.modules.exceptions import BPNotFound
from paasng.platform.modules.helpers import (
    ModuleRuntimeBinder,
    ModuleRuntimeManager,
    get_image_labels_by_module,
    update_build_config_with_method,
)
from paasng.platform.modules.manager import (
    ModuleCleaner,
    create_repo_with_platform_account,
    create_repo_with_user_account,
    delete_repo_on_error,
    init_module_in_view,
)
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
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.platform.templates.serializers import TemplateRenderOutputSLZ
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ModuleViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {
                "list": AppAction.VIEW_BASIC_INFO,
                "retrieve": AppAction.VIEW_BASIC_INFO,
            },
            default_action=AppAction.MANAGE_MODULE,
        ),
    ]

    @transaction.atomic
    @swagger_auto_schema(request_body=CreateModuleSLZ, tags=["创建模块"])
    def create(self, request, *args, **kwargs):
        """创建一个新模块, 创建 lesscode 模块时需要从cookie中获取用户登录信息,该 APIGW 不能直接注册到 APIGW 上提供"""
        application = self.get_application()
        self._ensure_allow_create_module(application)

        serializer = CreateModuleSLZ(data=request.data, context={"application": application})
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        source_init_template = data["source_init_template"]
        tmpl = Template.objects.get(name=source_init_template, type=TemplateType.NORMAL)

        # Permission check for non-default source origin
        source_origin = SourceOrigin(data["source_origin"])

        # lesscode app needs to create an application on the bk_lesscode platform first
        if source_origin == SourceOrigin.BK_LESS_CODE:
            bk_token = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
            try:
                make_bk_lesscode_client(login_cookie=bk_token, tenant_id=get_tenant(request.user).id).create_app(
                    application.code, application.name, data["name"]
                )
            except (LessCodeApiError, LessCodeGatewayServiceError) as e:
                raise error_codes.CREATE_LESSCODE_APP_ERROR.f(e.message)

        module = Module.objects.create(
            application=application,
            is_default=False,
            region=application.region,
            name=data["name"],
            language=tmpl.language,
            source_origin=data["source_origin"],
            source_init_template=source_init_template,
            owner=application.owner,
            creator=request.user.pk,
            tenant_id=application.tenant_id,
        )
        ret = init_module_in_view(
            module,
            data["source_control_type"],
            data["source_repo_url"],
            data["source_repo_auth_info"],
            # 新模块集群配置复用默认模块的
            env_cluster_names=get_app_cluster_names(application),
            source_dir=data["source_dir"],
        )

        return Response(
            data={
                "module": ModuleSLZ(module).data,
                "source_init_result": SourceInitResultSLZ(ret.source_init_result).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, code):
        """查看所有应用模块"""
        slz = ListModulesSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        application = self.get_application()
        modules = application.modules.all().order_by("-is_default", "name")

        # Filter modules by source_type
        if slz.data.get("source_origin"):
            modules = modules.filter(source_origin=slz.data["source_origin"])
        return Response(data=MinimalModuleSLZ(modules, many=True).data)

    @swagger_auto_schema(tags=["应用模块"], response_serializer=ModuleSLZ)
    def retrieve(self, request, code, module_name):
        """查看应用模块信息

        `web_config` 字段说明：

        - `templated_source_enabled`：模块使用是否了源码模板
        """
        application = self.get_application()
        module = application.get_module(module_name)
        return Response(data=ModuleSLZ(module).data, status=status.HTTP_200_OK)

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

        try:
            with transaction.atomic():
                module = application.get_module_with_lock(module_name=module_name)
                ModuleCleaner(module).clean()
        except Exception as e:
            logger.exception(
                "unable to clean module<%s> of application<%s> related resources", module_name, application.code
            )
            # 执行失败
            add_app_audit_record(
                app_code=application.code,
                tenant_id=application.tenant_id,
                user=request.user.pk,
                action_id=AppAction.MANAGE_MODULE,
                operation=OperationEnum.DELETE,
                target=OperationTarget.MODULE,
                attribute=module.name,
                result_code=ResultCode.FAILURE,
            )
            raise error_codes.CANNOT_DELETE_MODULE.f(str(e))

        # 执行成功
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.MANAGE_MODULE,
            operation=OperationEnum.DELETE,
            target=OperationTarget.MODULE,
            attribute=module.name,
            result_code=ResultCode.SUCCESS,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # [deprecated] use `api.applications.entrances.set_default_entrance` instead
    @transaction.atomic
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
                    _(
                        "目标 {module_name} 模块未满足应用市场服务开启条件，切换主模块会导致应用在市场中访问异常"
                    ).format(module_name=module_name)
                )

        logger.info(
            f"Switching default module for application[{application.code}], {default_module.name} -> {module.name}..."
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
    @swagger_auto_schema(request_body=CreateCNativeModuleSLZ, tags=["创建模块"])
    def create_cloud_native_module(self, request, code):
        """创建云原生应用模块（非默认）"""
        application = self.get_application()
        self._ensure_allow_create_module(application)

        serializer = CreateCNativeModuleSLZ(data=request.data, context={"application": application})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        module_src_cfg: Dict[str, Any] = {}
        source_config = data["source_config"]
        source_origin = SourceOrigin(source_config["source_origin"])

        module_src_cfg["source_origin"] = source_origin
        # 如果指定模板信息，则需要提取并保存
        if tmpl_name := source_config["source_init_template"]:
            tmpl = Template.objects.get(name=tmpl_name)
            module_src_cfg.update({"language": tmpl.language, "source_init_template": tmpl_name})

        module = Module.objects.create(
            application=application,
            is_default=False,
            region=application.region,
            name=data["name"],
            owner=application.owner,
            creator=request.user.pk,
            **module_src_cfg,
            tenant_id=application.tenant_id,
        )

        repo_type = source_config.get("source_control_type")
        repo_url = source_config.get("source_repo_url")
        repo_group = source_config.get("repo_group")
        repo_name = source_config.get("repo_name")
        username = request.user.username
        # 由平台创建代码仓库
        auto_repo_url = None
        if source_config.get("auto_create_repo"):
            if application.is_plugin_app:
                auto_repo_url = create_repo_with_platform_account(module, repo_type, username)
            else:
                auto_repo_url = create_repo_with_user_account(module, repo_type, repo_name, username, repo_group)
            repo_url = auto_repo_url

        user_id = request.user.pk
        with delete_repo_on_error(user_id, repo_type, auto_repo_url):
            ret = init_module_in_view(
                module,
                repo_type=repo_type,
                repo_url=repo_url,
                repo_auth_info=source_config.get("source_repo_auth_info"),
                source_dir=source_config.get("source_dir", ""),
                # 新模块集群配置复用默认模块的
                env_cluster_names=get_app_cluster_names(application),
                bkapp_spec=data["bkapp_spec"],
                write_template_to_repo=source_config.get("write_template_to_repo"),
            )

        return Response(
            data={
                "module": ModuleSLZ(module).data,
                "source_init_result": SourceInitResultSLZ(ret.source_init_result).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _ensure_allow_create_module(self, application: Application):
        """检查当前应用是否允许继续创建模块"""
        if not user_can_operate_in_region(self.request.user, application.region):
            raise error_codes.CANNOT_CREATE_MODULE.f(_("当前应用所属的版本不允许创建新模块"))

        if not AppSpecs(application).can_create_extra_modules:
            raise ValidationError(_("当前应用下不允许创建新模块"))

        modules_count = application.modules.count()
        if modules_count >= settings.MAX_MODULES_COUNT_PER_APPLICATION:
            raise error_codes.CREATE_MODULE_QUOTA_EXCEEDED.f(
                _("单个应用下最多能创建 {num} 个模块").format(num=settings.MAX_MODULES_COUNT_PER_APPLICATION)
            )

    def _init_image_credential(self, application: Application, image_credential: Dict):
        try:
            AppUserCredential.objects.create(
                application_id=application.id, tenant_id=application.tenant_id, **image_credential
            )
        except DbIntegrityError:
            raise error_codes.CREATE_CREDENTIALS_FAILED.f(_("同名凭证已存在"))


class ModuleRuntimeViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    # Deprecated: using ModuleBuildConfigViewSet
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list_available(self, request, code, module_name):
        """获取一个模块可用的运行环境"""
        application = self.get_application()
        module = application.get_module(module_name)

        results = []

        runtime_labels = get_image_labels_by_module(module)
        available_slugrunners = AppSlugRunner.objects.filter_by_labels(module, runtime_labels)
        if available_slugrunners.count() == 0:
            available_slugrunners = AppSlugRunner.objects.filter_module_available(module)
        slugrunners = {i.name: i for i in available_slugrunners}

        available_slugbuilders = AppSlugBuilder.objects.filter_by_labels(module, runtime_labels)
        if available_slugbuilders.count() == 0:
            available_slugbuilders = AppSlugBuilder.objects.filter_module_available(module)
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

    @staticmethod
    def _gen_build_config_data(module: Module, build_config: BuildConfig):
        info = {
            "build_method": build_config.build_method,
            "use_bk_ci_pipeline": build_config.use_bk_ci_pipeline,
        }
        if build_config.build_method == RuntimeType.BUILDPACK:
            runtime_manager = ModuleRuntimeManager(module)
            slugbuilder = runtime_manager.get_slug_builder(raise_exception=False)
            buildpacks = runtime_manager.list_buildpacks()
            info.update(
                env_image_repositories=generate_image_repositories_by_module(module),
                tag_options=build_config.tag_options,
                bp_stack_name=getattr(slugbuilder, "name", None),
                buildpacks=buildpacks,
            )
        elif build_config.build_method == RuntimeType.DOCKERFILE:
            info.update(
                env_image_repositories=generate_image_repositories_by_module(module),
                tag_options=build_config.tag_options,
                dockerfile_path=build_config.dockerfile_path,
                docker_build_args=build_config.docker_build_args,
            )
        else:
            info.update(
                image_repository=build_config.image_repository,
                image_credential_name=build_config.image_credential_name,
            )

        return ModuleBuildConfigSLZ(info).data

    @swagger_auto_schema(response_serializer=ModuleBuildConfigSLZ)
    def retrieve(self, request, code, module_name):
        """获取当前模块的构建配置"""
        module = self.get_module_via_path()
        build_config = BuildConfig.objects.get_or_create_by_module(module)

        return Response(data=self._gen_build_config_data(module, build_config))

    @swagger_auto_schema(request_body=ModuleBuildConfigSLZ)
    def modify(self, request, code, module_name):
        """修改当前模块的构建配置"""
        slz = ModuleBuildConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module = self.get_module_via_path()
        build_config = BuildConfig.objects.get_or_create_by_module(module)
        data_before = DataDetail(data=self._gen_build_config_data(module, build_config))

        build_method = data["build_method"]

        if build_method not in [RuntimeType.BUILDPACK, RuntimeType.DOCKERFILE, RuntimeType.CUSTOM_IMAGE]:
            raise error_codes.MODIFY_UNSUPPORTED.f(_("不支持的构建方式"))

        # 不允许修改构建方式（从仅镜像应用改成其他方式 / 其他方式改成仅镜像应用）
        if build_method != build_config.build_method and RuntimeType.CUSTOM_IMAGE in [
            build_method,
            build_config.build_method,
        ]:
            raise error_codes.MODIFY_UNSUPPORTED.f(_("当前模块不支持修改构建方式为 {}").format(build_method))

        try:
            update_build_config_with_method(build_config, build_method, data)
        except BPNotFound:
            raise error_codes.BIND_RUNTIME_FAILED.f(_("构建工具不存在"))

        add_app_audit_record(
            app_code=code,
            tenant_id=module.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BUILD_CONFIG,
            module_name=module_name,
            data_before=data_before,
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(response_serializer=ModuleRuntimeSLZ(many=True))
    def list_available_bp_runtimes(self, request, code, module_name):
        """获取一个模块可用的运行环境"""
        application = self.get_application()
        module = application.get_module(module_name)

        results = []
        runtime_labels = get_image_labels_by_module(module)
        available_slugrunners = AppSlugRunner.objects.filter_by_labels(module, runtime_labels)
        if available_slugrunners.count() == 0:
            available_slugrunners = AppSlugRunner.objects.filter_module_available(module)
        slugrunners = {i.name: i for i in available_slugrunners}

        available_slugbuilders = AppSlugBuilder.objects.filter_by_labels(module, runtime_labels)
        if available_slugbuilders.count() == 0:
            available_slugbuilders = AppSlugBuilder.objects.filter_module_available(module)
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
    """普通应用的「部署配置」API"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    schema = None

    @swagger_auto_schema(response_serializer=ModuleDeployConfigSLZ, deprecated=True)
    def retrieve(self, request, *args, **kwargs):
        """获取当前模块的部署配置信息"""
        module = self.get_module_via_path()

        return Response(
            ModuleDeployConfigSLZ(
                {
                    "hooks": [
                        {
                            "type": hook.type,
                            "command": hook.proc_command,
                            "enabled": hook.enabled,
                        }
                        for hook in module.deploy_hooks.all()
                    ],
                    "procfile": {
                        proc.name: proc.get_proc_command() for proc in ModuleProcessSpec.objects.filter(module=module)
                    },
                }
            ).data
        )

    @swagger_auto_schema(request_body=ModuleDeployHookSLZ, responses={204: openapi_empty_response}, deprecated=True)
    def upsert_hook(self, request, *args, **kwargs):
        """更新或创建当前模块的部署配置的钩子"""
        module = self.get_module_via_path()

        slz = ModuleDeployHookSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module.deploy_hooks.enable_hook(type_=data["type"], proc_command=data["command"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={204: openapi_empty_response}, deprecated=True)
    def disable_hook(self, request, code, module_name, type_: str):
        """禁用当前模块的部署配置的钩子"""
        module = self.get_module_via_path()

        try:
            module.deploy_hooks.disable_hook(DeployHookType(type_))
        except ValueError:
            raise ValidationError(detail={"type": f"“{type_}” 不是合法选项。"}, code="invalid_choice")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=ModuleDeployProcfileSLZ, response_serializer=ModuleDeployProcfileSLZ, deprecated=True
    )
    def update_procfile(self, request, *args, **kwargs):
        """更新或创建当前模块的部署配置的启动命令(目前旧镜像应用在用)"""
        module = self.get_module_via_path()
        if ModuleSpecs(module).runtime_type != RuntimeType.CUSTOM_IMAGE:
            raise ValidationError(_("当前应用不支持配置「启动命令」"))

        slz = ModuleDeployProcfileSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        procfile = slz.validated_data["procfile"]

        processes = [
            Process(name=proc_name, proc_command=proc_command) for proc_name, proc_command in procfile.items()
        ]
        sync_processes(module, processes, fieldmgr.FieldMgrName.APP_DESC, use_proc_command=True)

        return Response(
            ModuleDeployProcfileSLZ(
                {
                    "procfile": {
                        proc.name: proc.get_proc_command() for proc in ModuleProcessSpec.objects.filter(module=module)
                    }
                }
            ).data
        )


class ModuleTemplateViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(response_serializer=TemplateRenderOutputSLZ)
    def retrieve(self, request, code, module_name):
        """获取当前模块的初始化模板信息"""
        module = self.get_module_via_path()

        # 可能存在远古模版，并不在当前模版配置中
        template = get_object_or_404(Template, name=module.source_init_template)

        return Response(TemplateRenderOutputSLZ(template).data)
