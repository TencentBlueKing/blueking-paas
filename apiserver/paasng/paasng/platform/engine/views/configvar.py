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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.engine.configurations.config_var import (
    get_custom_builtin_config_vars,
    list_conflicted_env_vars_for_view,
    list_vars_builtin_app_basic,
    list_vars_builtin_plat_addrs,
    list_vars_builtin_region,
    list_vars_builtin_runtime,
    mask_vars_for_view,
)
from paasng.platform.engine.configurations.env_var.entities import EnvVariableList
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models import ConfigVar
from paasng.platform.engine.models.config_var import (
    ENVIRONMENT_ID_FOR_GLOBAL,
    ENVIRONMENT_NAME_FOR_GLOBAL,
)
from paasng.platform.engine.models.managers import ConfigVarManager, ExportedConfigVars, PlainConfigVar
from paasng.platform.engine.serializers import (
    ConfigVarApplyResultSLZ,
    ConfigVarBaseInputSLZ,
    ConfigVarBatchInputSLZ,
    ConfigVarImportSLZ,
    ConfigVarOperateAuditOutputSLZ,
    ConfigVarSLZ,
    ConfigVarUpsertByKeyInputSLZ,
    ConflictedEnvVarInfoOutputSLZ,
    CreateConfigVarInputSLZ,
    ListBuiltinConfigVarSLZ,
    ListConfigVarsQuerySLZ,
    UpdateConfigVarInputSLZ,
)


class ConfigVarViewSet(viewsets.ModelViewSet, ApplicationCodeInPathMixin):
    """ViewSet for config vars"""

    pagination_class = None
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
        data_before = DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data))

        slz = CreateConfigVarInputSLZ(data=request.data, context={"module": self.get_module_via_path()})
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
            data_after=DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=ConfigVarSLZ, tags=["环境配置"], responses={200: ConfigVarSLZ()})
    def update(self, request, *args, **kwargs):
        """更新环境变量"""
        config_var = self.get_object()
        data_before = DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data))

        slz = UpdateConfigVarInputSLZ(config_var, data=request.data, context={"module": self.get_module_via_path()})
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
            data_after=DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data)),
        )

        return Response(slz.data)

    @swagger_auto_schema(tags=["环境配置"], responses={204: ""})
    def destroy(self, request, *args, **kwargs):
        """删除环境变量"""
        config_var = self.get_object()
        data_before = DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data))
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
            data_after=DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(tags=["环境配置"], responses={status.HTTP_200_OK: ConfigVarSLZ(many=True)})
    def retrieve_by_key(self, request, code, module_name, config_vars_key):
        """通过环境变量的 key 获取环境变量"""
        config_vars = self.get_queryset().filter(key=config_vars_key)
        serializer = ConfigVarSLZ(config_vars, context={"module": self.get_module_via_path()}, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=ConfigVarUpsertByKeyInputSLZ,
        tags=["环境配置"],
        responses={status.HTTP_200_OK: None},
    )
    def upsert_by_key(self, request, code, module_name, config_vars_key):
        """通过环境变量的 key 更新或创建环境变量"""
        data = request.data.copy()
        data["key"] = config_vars_key
        module = self.get_module_via_path()
        slz = ConfigVarBaseInputSLZ(data=data, context={"module": module})
        slz.is_valid(raise_exception=True)
        config_var = slz.validated_data

        # 查询是否已存在相同 key 和 env 的变量
        existing_vars = ConfigVar.objects.filter(
            module=module, key=config_vars_key, environment_id__environment=config_var.environment_name
        )

        if existing_vars.exists():
            # 存在该变量, 进行更新操作
            # 构建更新字段字典，如果 value 为空则不更新 value 字段
            _update_fields = {"description": config_var.description}
            if config_var.value:
                _update_fields["value"] = config_var.value
            existing_vars.update(**_update_fields)
        else:
            # 不存在该变量，进行创建操作
            # 创建之前, 验证 value 是否传入
            if not config_var.value:
                raise ValidationError({"value": "value is required"})
            ConfigVar.objects.create(
                module=module,
                key=config_vars_key,
                environment_id=config_var.environment_id,
                value=config_var.value,
                is_sensitive=config_var.is_sensitive,
                description=config_var.description,
                is_global=config_var.is_global,
            )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["环境配置"], responses={201: ConfigVarApplyResultSLZ()})
    def clone(self, request, **kwargs):
        """从某一模块克隆环境变量至当前模块"""
        data_before = DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data))

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
            data_after=DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=ConfigVarBatchInputSLZ(many=True),
        tags=["环境配置"],
        responses={201: ConfigVarApplyResultSLZ()},
    )
    def batch(self, request, **kwargs):
        """
        批量保存环境变量

        前端传值格式:
        [
            {
                "id": 123,                 # 已存在则传id, 新增则不传
                "key": "ENV_KEY",          # 环境变量名
                "value": "xxx",            # 环境变量值 (新增必填，更新可选)
                "is_sensitive": true,      # (可选, 默认为 false), 决定 value 是否敏感, 更新时忽略该字段的修改
                "description": "desc",     # 变量描述
                "environment_name": "prod" # 生效环境, 可选值: "prod", "stag", "_global_"
            },
        ]

        后端处理逻辑:
        - 有id且数据库存在该id, 则为更新, value可不传 (不传则不更新value字段)
        - 无id或id不存在, 则为新增, value字段必填
        - 校验通过后, 批量保存环境变量, 返回新增/更新/忽略的数量统计

        返回值：
        {
            "create_num": 0,     # 新增数量,
            "overwrited_num": 1, # 更新数量,
            "deleted_num":1      # 删除数量
        }
        """
        data_before = DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data))

        module = self.get_module_via_path()
        slz = ConfigVarBatchInputSLZ(data=request.data, context={"module": module}, many=True)
        slz.is_valid(raise_exception=True)
        env_variables = slz.validated_data

        # # 检验数据, 新建的 ConfigVar 需要传入 value
        # instance_list = module.configvar_set.filter(is_builtin=False).prefetch_related("environment")
        # instance_mapping = {obj.id: obj for obj in instance_list}
        # for var_data in env_variables:
        #     if (not var_data.id or var_data.id not in instance_mapping) and not var_data.value:
        #         raise ValidationError({"value": "value is required when create"})

        try:
            apply_result = ConfigVarManager().batch_save(module, env_variables)
        except ValueError as e:
            raise ValidationError(e.args[0])
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
            data_after=DataDetail(data=list(ConfigVarOperateAuditOutputSLZ(self.get_queryset(), many=True).data)),
        )
        return Response(res.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        query_serializer=ListConfigVarsQuerySLZ(),
        tags=["环境配置"],
        responses={200: ConfigVarSLZ(many=True)},
    )
    def list(self, request, **kwargs):
        """查看应用的所有环境变量"""
        input_slz = ListConfigVarsQuerySLZ(data=request.query_params)
        input_slz.is_valid(raise_exception=True)

        config_vars = self.get_queryset()

        # Filter by environment name
        environment_name = input_slz.data.get("environment_name")
        if environment_name:
            config_vars = config_vars.filter_by_environment_name(ConfigVarEnvName(environment_name))

        # Change result ordering
        config_vars = config_vars.order_by(input_slz.data["order_by"], "is_global")

        serializer = ConfigVarSLZ(config_vars, context={"module": self.get_module_via_path()}, many=True)
        return Response(serializer.data)


class ConfigVarBuiltinViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """View the built-in environment variables of the app module"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(tags=["环境配置"], responses={200: ListBuiltinConfigVarSLZ(many=True)})
    def list_builtin_envs(self, request, code, module_name):
        """获取内置环境变量"""
        module = self.get_module_via_path()
        app = module.application

        result = {}
        for env in module.get_envs():
            env_vars = EnvVariableList()

            # 应用基本信息环境变量
            env_vars.extend(list_vars_builtin_app_basic(app=app, include_deprecated=False))

            # 蓝鲸体系内平台的访问地址
            env_vars.extend(list_vars_builtin_plat_addrs())

            # 需要根据 region、env 写入不同值的系统环境变量
            env_vars.extend(list_vars_builtin_region(app.region, env.environment))

            # 平台管理中自定义的环境变量
            env_vars.extend(get_custom_builtin_config_vars())

            # 应用运行时相关环境变量
            env_vars.extend(list_vars_builtin_runtime(env=env, include_deprecated=False))

            # 使用 map 去重后转化为 EnvVariableList, 并按照 key 排序
            sorted_vars = sorted(env_vars.map.values(), key=lambda v: v.key.lower())
            deduped_vars = EnvVariableList(sorted_vars)
            result[env.environment] = mask_vars_for_view(deduped_vars)

        return Response(ListBuiltinConfigVarSLZ(result).data)


class ConfigVarImportExportViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def make_file_response(file_content: str, file_name: str) -> HttpResponse:
        """Generate http response(with attachment)"""

        response = HttpResponse(file_content, content_type="application/octet-stream")
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

    @swagger_auto_schema(query_serializer=ListConfigVarsQuerySLZ(), tags=["环境配置"])
    def export_to_file(self, request, code, module_name):
        """导出环境变量到文件"""
        list_vars_slz = ListConfigVarsQuerySLZ(data=request.query_params)
        list_vars_slz.is_valid(raise_exception=True)
        order_by = list_vars_slz.data["order_by"]

        queryset = (
            self.get_queryset()
            .filter(is_builtin=False)
            .prefetch_related("environment")
            .order_by(order_by, "is_global")
        )

        # 统计总数和过滤敏感变量
        filtered_queryset = queryset.filter(is_sensitive=False)
        ignored_keys = list(queryset.filter(is_sensitive=True).values_list("key", flat=True))

        result = ExportedConfigVars.from_list(list(filtered_queryset))
        file_content = result.to_file_content(extra_cmt=f"# 已忽略 {len(ignored_keys)} 条敏感环境变量: {ignored_keys}")
        return self.make_file_response(file_content, f"{self.get_application().code}_{module_name}_config_vars.yaml")

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

        file_content = config_vars.to_file_content()
        return self.make_file_response(file_content, "bk_paas3_config_vars_template.yaml")


class ConflictedConfigVarsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """与内置变量冲突的用户环境变量相关 ViewSet"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        responses={200: ConflictedEnvVarInfoOutputSLZ(many=True)},
    )
    def list_configvar_conflicted_keys(self, request, code, module_name):
        """获取环境变量及其可覆盖性

        “冲突”指用户自定义变量与平台内置变量同名。 不同类型的应用，平台处理冲突变量的行为有所不同，
        本接口返回的 key 列表主要作引导和提示用。

        客户端展示建议：

        - 对于 conflicted_source 为 builtin_addons 的增强服务环境变量冲突，建议前端读取 conflicted_detail
          直接详细展示与哪一个环境变量冲突。
        - 其他 conflicted_source 建议统一展示为“与平台内置变量冲突”，然后补充 conflicted_detail 里的信息。
        - 按照 override_conflicted 字段的值，展示字段已经覆盖冲突项，是否生效。
        """
        module = self.get_module_via_path()
        conflicted_env_vars = list_conflicted_env_vars_for_view(module)
        return Response(ConflictedEnvVarInfoOutputSLZ(conflicted_env_vars, many=True).data)
