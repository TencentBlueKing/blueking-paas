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
from typing import Dict

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.engine.configurations.config_var import (
    generate_env_vars_by_region_and_env,
    generate_env_vars_for_bk_platform,
)
from paasng.engine.constants import AppInfoBuiltinEnv, AppRunTimeBuiltinEnv, NoPrefixAppRunTimeBuiltinEnv
from paasng.engine.models import ConfigVar
from paasng.engine.models.config_var import add_prefix_to_key
from paasng.engine.models.managers import ConfigVarManager, ExportedConfigVars, PlainConfigVar
from paasng.engine.serializers import (
    ConfigVarApplyResultSLZ,
    ConfigVarFormatSLZ,
    ConfigVarImportSLZ,
    ConfigVarSLZ,
    ListConfigVarsSLZ,
)
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes


@method_decorator(name="update", decorator=swagger_auto_schema(request_body=ConfigVarSLZ, tags=['环境配置']))
@method_decorator(name="create", decorator=swagger_auto_schema(request_body=ConfigVarSLZ, tags=['环境配置']))
@method_decorator(name="list", decorator=swagger_auto_schema(query_serializer=ListConfigVarsSLZ, tags=['环境配置']))
@method_decorator(name="destroy", decorator=swagger_auto_schema(tags=['环境配置']))
class ConfigVarViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """ViewSet for config vars"""

    pagination_class = None
    serializer_class = ConfigVarSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def get_object(self):
        """Get current ConfigVar object by path var"""
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['id'])

    def get_queryset(self):
        return ConfigVar.objects.filter(module=self.get_module_via_path(), is_builtin=False)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["module"] = self.get_module_via_path()
        return context

    @swagger_auto_schema(
        tags=['环境配置'],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def clone(self, request, **kwargs):
        """从某一模块克隆环境变量至当前模块"""
        application = self.get_application()
        source = application.get_module(module_name=self.kwargs['source_module_name'])
        dest = self.get_module_via_path()

        res_nums = ConfigVarManager().clone_vars(source, dest)

        slz = ConfigVarApplyResultSLZ(res_nums)
        return Response(slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=ConfigVarFormatSLZ,
        tags=['环境配置'],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def batch(self, request, **kwargs):
        """批量保存环境变量"""
        module = self.get_module_via_path()
        slz = ConfigVarFormatSLZ(data=request.data, context={"module": module}, many=True)
        slz.is_valid(raise_exception=True)
        env_variables = slz.validated_data

        apply_result = ConfigVarManager().apply_vars_to_module(module, env_variables)
        res = ConfigVarApplyResultSLZ(apply_result)
        return Response(res.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(query_serializer=ListConfigVarsSLZ, tags=['环境配置'], responses={200: ConfigVarSLZ(many=True)})
    def list(self, request, **kwargs):
        """查看应用的所有环境变量"""
        input_slz = ListConfigVarsSLZ(data=request.query_params)
        input_slz.is_valid(raise_exception=True)

        config_vars = self.get_queryset().select_related('environment')

        # Filter by environment name
        environment_name = input_slz.data.get('environment_name')
        if environment_name:
            config_vars = config_vars.filter_by_environment_name(environment_name)

        # Change result ordering
        config_vars = config_vars.order_by(input_slz.data['order_by'], 'is_global')

        serializer = self.serializer_class(config_vars, many=True)
        return Response(serializer.data)


class ConfigVarBuiltinViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """View the built-in environment variables of the app"""

    def _get_enum_choices_dict(self, EnumObj) -> Dict[str, str]:
        return {field[0]: field[1] for field in EnumObj.get_choices()}

    def get_builtin_envs_for_app(self, request, code):
        env_dict = self._get_enum_choices_dict(AppInfoBuiltinEnv)
        return Response(add_prefix_to_key(env_dict, settings.CONFIGVAR_SYSTEM_PREFIX))

    def get_builtin_envs_bk_platform(self, request, code):
        bk_address_envs = generate_env_vars_for_bk_platform(settings.CONFIGVAR_SYSTEM_PREFIX)

        application = self.get_application()
        region = application.region
        # 默认展示正式环境的环境变量
        environment = AppEnvironment.PRODUCTION.value
        envs_by_region_and_env = generate_env_vars_by_region_and_env(
            region, environment, settings.CONFIGVAR_SYSTEM_PREFIX
        )

        return Response({**bk_address_envs, **envs_by_region_and_env})

    def get_runtime_envs(self, request, code):
        env_dict = self._get_enum_choices_dict(AppRunTimeBuiltinEnv)
        envs = add_prefix_to_key(env_dict, settings.CONFIGVAR_SYSTEM_PREFIX)

        no_prefix_envs = self._get_enum_choices_dict(NoPrefixAppRunTimeBuiltinEnv)
        return Response({**envs, **no_prefix_envs})


class ConfigVarImportExportViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def make_exported_vars_response(data: ExportedConfigVars, file_name: str) -> HttpResponse:
        """Generate http response(with attachment) for given config vars data

        :param data: config vars data
        :param file_name: attachment filename
        """
        response = HttpResponse(data.to_file_content(), content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    def get_queryset(self):
        return ConfigVar.objects.filter(module=self.get_module_via_path(), is_builtin=False)

    @swagger_auto_schema(
        request_body=ConfigVarImportSLZ,
        tags=['环境配置'],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def import_by_file(self, request, **kwargs):
        """从文件导入环境变量"""
        module = self.get_module_via_path()
        # Check file format
        try:
            slz = ConfigVarImportSLZ(data=request.FILES, context={"module": module})
            slz.is_valid(raise_exception=True)
        except ValidationError as e:
            raise getattr(error_codes, e.get_codes()["error"], e)

        # Import config vars
        env_variables = slz.validated_data["env_variables"]

        apply_result = ConfigVarManager().apply_vars_to_module(module, env_variables)
        res = ConfigVarApplyResultSLZ(apply_result)
        return Response(res.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=['环境配置'])
    def export_to_file(self, request, code, module_name):
        """导出环境变量到文件"""
        list_vars_slz = ListConfigVarsSLZ(data=request.query_params)
        list_vars_slz.is_valid(raise_exception=True)
        order_by = list_vars_slz.data['order_by']

        queryset = (
            self.get_queryset().filter(is_builtin=False).select_related('environment').order_by(order_by, 'is_global')
        )

        result = ExportedConfigVars.from_list(list(queryset))
        return self.make_exported_vars_response(result, f"bk_paas3_{code}_{module_name}_config_vars.yaml")

    @swagger_auto_schema(tags=['环境配置'])
    def template(self, request, **kwargs):
        """返回yaml模板"""
        config_vars = ExportedConfigVars(
            env_variables=[
                PlainConfigVar(key="PROD", value="example", environment_name="prod", description="example"),
                PlainConfigVar(key="STAG", value="example", environment_name="stag", description="example"),
                PlainConfigVar(key="GLOBAL", value="example", environment_name="_global_", description="example"),
            ]
        )
        return self.make_exported_vars_response(config_vars, 'bk_paas3_config_vars_template.yaml')
