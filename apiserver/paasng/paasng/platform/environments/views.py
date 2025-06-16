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


from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import app_view_actions_perm
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.environments.utils import batch_save_protections

from . import serializers
from .constants import EnvRoleOperation
from .models import EnvRoleProtection


class ModuleEnvRoleProtectionViewSet(ApplicationCodeInPathMixin, viewsets.GenericViewSet):
    queryset = EnvRoleProtection.objects.all()
    serializer_class = serializers.EnvRoleProtectionSLZ
    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {
                "list": AppAction.VIEW_BASIC_INFO,
            },
            default_action=AppAction.MANAGE_ENV_PROTECTION,
        ),
    ]

    def get_envs(self, module_name, env):
        application = self.get_application()
        module = application.get_module(module_name)
        return module.get_envs(env)

    def list(self, request, code, module_name):
        """获取环境限制详情"""
        serializer = serializers.EnvRoleProtectionListSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        envs = self.get_envs(module_name, serializer.validated_data.get("env", None))
        operation = serializer.validated_data.get("operation")
        allowed_roles = serializer.validated_data.get("allowed_roles") or EnvRoleOperation.get_default_role(operation)
        protections = self.queryset.filter(module_env__in=envs, operation=operation, allowed_role__in=allowed_roles)

        return Response(data=self.serializer_class(protections, many=True).data)

    def toggle(self, request, code, module_name):
        """开启或关闭环境限制"""
        serializer = serializers.EnvRoleProtectionCreateSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        env = self.get_envs(module_name, serializer.validated_data["env"])
        operation = serializer.validated_data.get("operation")
        # toggle 接口目前只支持默认角色开关，如果要支持更多的角色自定义，需要另添加 create & delete 接口
        allowed_roles = EnvRoleOperation.get_default_role(operation)

        protections = self.queryset.filter(module_env=env, operation=operation, allowed_role__in=allowed_roles)
        if protections:
            protections.delete()
            add_app_audit_record(
                app_code=code,
                tenant_id=env.tenant_id,
                user=request.user.pk,
                action_id=AppAction.MANAGE_ENV_PROTECTION,
                operation=OperationEnum.DISABLE,
                target=OperationTarget.DEPLOY_RESTRICTION,
                module_name=module_name,
                environment=env.environment,
            )
            return Response(data=[])

        protections = []
        for role in allowed_roles:
            protections.append(
                EnvRoleProtection(module_env=env, operation=operation, allowed_role=role, tenant_id=env.tenant_id)
            )

        protections = EnvRoleProtection.objects.bulk_create(protections)

        add_app_audit_record(
            app_code=code,
            tenant_id=env.tenant_id,
            user=request.user.pk,
            action_id=AppAction.MANAGE_ENV_PROTECTION,
            operation=OperationEnum.ENABLE,
            target=OperationTarget.DEPLOY_RESTRICTION,
            module_name=module_name,
            environment=env.environment,
        )
        return Response(self.serializer_class(protections, many=True).data)

    @swagger_auto_schema(
        request_body=serializers.BatchEnvRoleProtectionSLZ,
        tags=["部署限制"],
    )
    def batch_save(self, request, code, module_name):
        """批量保存环境限制设置"""
        application = self.get_application()
        module = application.get_module(module_name)

        serializer = serializers.BatchEnvRoleProtectionSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        operation = data.get("operation")
        # 目前产品上只支持默认角色(开发)
        allowed_roles = EnvRoleOperation.get_default_role(operation)

        qs = EnvRoleProtection.objects.filter(
            module_env__module=module, operation=operation, allowed_role__in=allowed_roles
        )
        data_before = []
        for item in qs:
            data_before.append(item.module_env.environment)

        qs = batch_save_protections(module, operation, allowed_roles, data["envs"])

        add_app_audit_record(
            app_code=code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.MANAGE_ENV_PROTECTION,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.DEPLOY_RESTRICTION,
            module_name=module_name,
            data_before=DataDetail(data=data_before),
            data_after=DataDetail(data=data["envs"]),
        )
        return Response(self.serializer_class(qs, many=True).data)
