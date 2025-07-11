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

from typing import Dict

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.configurations.config_var import (
    generate_env_vars_by_region_and_env,
    generate_env_vars_for_bk_platform,
    generate_wl_builtin_env_vars,
    get_user_conflicted_keys,
)
from paasng.platform.engine.constants import (
    AppInfoBuiltinEnv,
    AppRunTimeBuiltinEnv,
    ConfigVarEnvName,
)
from paasng.platform.engine.models import ConfigVar
from paasng.platform.engine.models.config_var import (
    ENVIRONMENT_ID_FOR_GLOBAL,
    ENVIRONMENT_NAME_FOR_GLOBAL,
    add_prefix_to_key,
)
from paasng.platform.engine.models.managers import ConfigVarManager, ExportedConfigVars, PlainConfigVar
from paasng.platform.engine.serializers import (
    ConfigVarApplyResultSLZ,
    ConfigVarFormatSLZ,
    ConfigVarFormatWithIdSLZ,
    ConfigVarImportSLZ,
    ConfigVarSLZ,
    ConfigVarWithoutKeyFormatSLZ,
    ConflictedKeyOutputSLZ,
    ListConfigVarsSLZ,
)


class ConfigVarViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """ViewSet for config vars"""

    pagination_class = None
    serializer_class = ConfigVarSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_object(self):
        """Get current ConfigVar object by path var"""
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["id"])

    def get_queryset(self):
        return ConfigVar.objects.filter(module=self.get_module_via_path(), is_builtin=False)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["module"] = self.get_module_via_path()
        return context

    @swagger_auto_schema(request_body=ConfigVarSLZ, tags=["环境配置"], responses={201: ""})
    def create(self, request, *args, **kwargs):
        """创建环境变量"""
        data_before = DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data))

        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        application = self.get_application()
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ENV_VAR,
            module_name=self.get_module_via_path().name,
            environment=request.data["environment_name"],
            data_before=data_before,
            data_after=DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=ConfigVarSLZ, tags=["环境配置"], responses={200: ConfigVarSLZ()})
    def update(self, request, *args, **kwargs):
        """更新环境变量"""
        config_var = self.get_object()
        data_before = DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data))

        slz = self.get_serializer(config_var, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        application = self.get_application()
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            module_name=config_var.module.name,
            environment=request.data["environment_name"],
            data_before=data_before,
            data_after=DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data)),
        )

        return Response(slz.data)

    @swagger_auto_schema(tags=["环境配置"], responses={204: ""})
    def destroy(self, request, *args, **kwargs):
        """删除环境变量"""
        config_var = self.get_object()
        data_before = DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data))
        config_var.delete()

        env = ENVIRONMENT_NAME_FOR_GLOBAL
        if config_var.environment_id != ENVIRONMENT_ID_FOR_GLOBAL:
            env = config_var.environment.environment
        application = self.get_application()
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            module_name=config_var.module.name,
            environment=env,
            data_before=data_before,
            data_after=DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        query_serializer=ListConfigVarsSLZ(),
        tags=["环境配置"],
        responses={status.HTTP_200_OK: ConfigVarSLZ(many=True)},
    )
    def retrieve_by_key(self, request, code, module_name, config_vars_key):
        """通过环境变量的 key 获取环境变量"""
        config_vars = self.get_queryset().filter(key=config_vars_key)
        serializer = self.serializer_class(config_vars, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=ConfigVarWithoutKeyFormatSLZ,
        tags=["环境配置"],
        responses={status.HTTP_200_OK: None},
    )
    def upsert_by_key(self, request, code, module_name, config_vars_key):
        """通过环境变量的 key 更新或创建环境变量"""
        data = request.data.copy()
        data["key"] = config_vars_key
        module = self.get_module_via_path()
        slz = ConfigVarFormatSLZ(data=data, context={"module": module})
        slz.is_valid(raise_exception=True)
        config_var = slz.validated_data

        # 查询是否已存在相同 key 和 env 的变量
        existing_vars = ConfigVar.objects.filter(
            module=module, key=config_vars_key, environment_id__environment=config_var.environment_name
        )

        if existing_vars.exists():
            # 存在, 更新已有记录
            existing_vars.update(value=config_var.value, description=config_var.description)
        else:
            # 不存在，创建新记录
            ConfigVar.objects.create(
                module=module,
                key=config_vars_key,
                environment_id=config_var.environment_id,
                value=config_var.value,
                description=config_var.description,
                is_global=config_var.is_global,
            )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["环境配置"], responses={201: ConfigVarApplyResultSLZ()})
    def clone(self, request, **kwargs):
        """从某一模块克隆环境变量至当前模块"""
        data_before = DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data))

        application = self.get_application()
        source = application.get_module(module_name=self.kwargs["source_module_name"])
        dest = self.get_module_via_path()

        res_nums = ConfigVarManager().clone_vars(source, dest)

        slz = ConfigVarApplyResultSLZ(res_nums)

        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            module_name=self.kwargs["source_module_name"],
            data_before=data_before,
            data_after=DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=ConfigVarFormatWithIdSLZ(many=True),
        tags=["环境配置"],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def batch(self, request, **kwargs):
        """批量保存环境变量"""
        data_before = DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data))

        module = self.get_module_via_path()
        slz = ConfigVarFormatWithIdSLZ(data=request.data, context={"module": module}, many=True)
        slz.is_valid(raise_exception=True)
        env_variables = slz.validated_data

        apply_result = ConfigVarManager().batch_save(module, env_variables)
        res = ConfigVarApplyResultSLZ(apply_result)

        application = self.get_application()
        add_app_audit_record(
            app_code=application.code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            module_name=module.name,
            data_before=data_before,
            data_after=DataDetail(data=list(ConfigVarFormatSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(res.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        query_serializer=ListConfigVarsSLZ(),
        tags=["环境配置"],
        responses={200: ConfigVarSLZ(many=True)},
    )
    def list(self, request, **kwargs):
        """查看应用的所有环境变量"""
        input_slz = ListConfigVarsSLZ(data=request.query_params)
        input_slz.is_valid(raise_exception=True)

        config_vars = self.get_queryset()

        # Filter by environment name
        environment_name = input_slz.data.get("environment_name")
        if environment_name:
            config_vars = config_vars.filter_by_environment_name(ConfigVarEnvName(environment_name))

        # Change result ordering
        config_vars = config_vars.order_by(input_slz.data["order_by"], "is_global")

        serializer = self.serializer_class(config_vars, many=True)
        return Response(serializer.data)


class ConfigVarBuiltinViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """View the built-in environment variables of the app"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def _get_enum_choices_dict(self, enum_obj) -> Dict[str, str]:
        return {field[0]: field[1] for field in enum_obj.get_choices()}

    def get_builtin_envs_for_app(self, request, code):
        env_dict = self._get_enum_choices_dict(AppInfoBuiltinEnv)
        return Response(add_prefix_to_key(env_dict, settings.CONFIGVAR_SYSTEM_PREFIX))

    def get_builtin_envs_bk_platform(self, request, code):
        bk_address_envs = generate_env_vars_for_bk_platform(settings.CONFIGVAR_SYSTEM_PREFIX)
        bk_address_envs_list = [env.to_dict() for env in bk_address_envs]

        application = self.get_application()
        region = application.region
        # 默认展示正式环境的环境变量
        environment = AppEnvironment.PRODUCTION.value
        envs_by_region_and_env = generate_env_vars_by_region_and_env(
            region, environment, settings.CONFIGVAR_SYSTEM_PREFIX
        )
        envs_by_region_and_env_list = [env.to_dict() for env in envs_by_region_and_env]

        builtin_envs_bk_platform = {}
        for env_dict in bk_address_envs_list + envs_by_region_and_env_list:
            builtin_envs_bk_platform.update(env_dict)
        return Response(builtin_envs_bk_platform)

    def get_runtime_envs(self, request, code):
        env_dict = self._get_enum_choices_dict(AppRunTimeBuiltinEnv)
        envs = add_prefix_to_key(env_dict, settings.CONFIGVAR_SYSTEM_PREFIX)

        wl_vars = generate_wl_builtin_env_vars(settings.CONFIGVAR_SYSTEM_PREFIX)
        for env in wl_vars:
            # Transform the dict structure to remove the value field in order to
            # keep consistent and be compatible with the frontend.
            # TODO: Show the value in the future.
            envs.update({k: v["description"] for k, v in env.to_dict().items()})
        return Response({**envs})


class ConfigVarImportExportViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def make_exported_vars_response(data: ExportedConfigVars, file_name: str) -> HttpResponse:
        """Generate http response(with attachment) for given config vars data

        :param data: config vars data
        :param file_name: attachment filename
        """
        response = HttpResponse(data.to_file_content(), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response

    def get_queryset(self):
        return ConfigVar.objects.filter(module=self.get_module_via_path(), is_builtin=False)

    @swagger_auto_schema(
        request_body=ConfigVarImportSLZ,
        tags=["环境配置"],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def import_by_file(self, request, **kwargs):
        """从文件导入环境变量"""
        module = self.get_module_via_path()
        # Check file format
        slz = ConfigVarImportSLZ(data=request.FILES, context={"module": module})
        slz.is_valid(raise_exception=True)

        # Import config vars
        env_variables = slz.validated_data["env_variables"]

        apply_result = ConfigVarManager().apply_vars_to_module(module, env_variables)
        res = ConfigVarApplyResultSLZ(apply_result)
        return Response(res.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["环境配置"])
    def export_to_file(self, request, code, module_name):
        """导出环境变量到文件"""
        list_vars_slz = ListConfigVarsSLZ(data=request.query_params)
        list_vars_slz.is_valid(raise_exception=True)
        order_by = list_vars_slz.data["order_by"]

        queryset = (
            self.get_queryset()
            .filter(is_builtin=False)
            .prefetch_related("environment")
            .order_by(order_by, "is_global")
        )

        result = ExportedConfigVars.from_list(list(queryset))
        return self.make_exported_vars_response(result, f"bk_paas3_{code}_{module_name}_config_vars.yaml")

    @swagger_auto_schema(tags=["环境配置"])
    def template(self, request, **kwargs):
        """返回yaml模板"""
        config_vars = ExportedConfigVars(
            env_variables=[
                PlainConfigVar(key="PROD", value="example", environment_name="prod", description="example"),
                PlainConfigVar(key="STAG", value="example", environment_name="stag", description="example"),
                PlainConfigVar(key="GLOBAL", value="example", environment_name="_global_", description="example"),
            ]
        )
        return self.make_exported_vars_response(config_vars, "bk_paas3_config_vars_template.yaml")


class ConflictedConfigVarsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """与内置变量冲突的用户环境变量相关 ViewSet"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_user_conflicted_keys(self, request, code, module_name):
        """获取当前模块中有冲突的环境变量 Key 列表，“冲突”指用户自定义变量与平台内置变量同名。
        不同类型的应用，平台处理冲突变量的行为有所不同，本接口返回的 key 列表主要作引导和提示用。

        客户端展示建议：

        - 对于 conflicted_source 为 builtin_addons 的增强服务环境变量冲突，建议前端读取 conflicted_detail
          直接详细展示与哪一个环境变量冲突。
        - 其他 conflicted_source 建议统一展示为“与平台内置变量冲突”，然后补充 conflicted_detail 里的信息。
        - 按照 override_conflicted 字段的值，展示字段已经覆盖冲突项，是否生效。
        """
        module = self.get_module_via_path()
        keys = get_user_conflicted_keys(module)
        return Response(ConflictedKeyOutputSLZ(keys, many=True).data)
