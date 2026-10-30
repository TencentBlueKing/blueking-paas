# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""应用态 (系统 API) 视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV / AppSpark 等固定的系统调用, 鉴权依赖 sysapi_client.
"""

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import AccessType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.platform.engine.deploy.interruptions import interrupt_deployment
from paasng.platform.engine.exceptions import DeployInterruptionFailed
from paasng.platform.engine.serializers import (
    CreateDeploymentResponseSLZ,
    DeploymentResultQuerySLZ,
    DeploymentResultSLZ,
    OfflineOperationSLZ,
    SysCreateDeploymentSLZ,
    SysCreateOfflineOperationSLZ,
    SysInterruptDeploymentSLZ,
)
from paasng.utils.error_codes import error_codes

from .deploy import DeploymentCreateMixin, get_module_deployment, render_deployment_result
from .misc import OfflineMixin


class SysDeploymentViewSet(DeploymentCreateMixin, viewsets.ViewSet, SysManagedAppInPathMixin):
    """应用态部署接口：AIDEV 只能操作 AI Agent 应用，AppSpark 只能操作 AppSpark 应用。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.DEPLOY_APPLICATIONS)]

    @swagger_auto_schema(
        request_body=SysCreateDeploymentSLZ,
        responses={"201": CreateDeploymentResponseSLZ()},
        tags=["部署相关接口"],
        operation_description="提供给 AIDEV / AppSpark 使用的应用态部署接口，只能操作调用方管理的应用",
    )
    def deploy(self, request, code, module_name, environment):
        """应用态部署应用，只允许操作调用方管理的应用，AppSpark 只能部署生产环境。"""
        env = self.get_managed_env_via_path()

        serializer = SysCreateDeploymentSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.data
        if params["advanced_options"].get("debug_enabled"):
            raise error_codes.CANNOT_DEPLOY_APP.f(_("应用态部署不支持构建调试"))

        # operator 仅用于记录操作人，不做 IAM 角色校验：AIDEV 将用户加入应用成员后，IAM 权限存在生效延迟
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, params["operator"]))
        deployment = self.do_deploy(env, params, operator)
        return JsonResponse(
            data={"deployment_id": deployment.id, "stream_url": f"/streams/{deployment.id}"},
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        responses={200: DeploymentResultSLZ},
        query_serializer=DeploymentResultQuerySLZ(),
        paginator_inspectors=[],
        tags=["部署相关接口"],
    )
    def get_deployment_result(self, request, code, module_name, uuid):
        """应用态查询部署任务结果，只允许查询调用方管理的应用。"""
        query_slz = DeploymentResultQuerySLZ(data=request.query_params)
        query_slz.is_valid(raise_exception=True)
        deployment = get_module_deployment(self.get_managed_module_via_path(), uuid)
        self.ensure_env_allowed_for_client(deployment.app_environment.environment)
        return JsonResponse(render_deployment_result(deployment, query_slz.validated_data["include_ansi_codes"]))

    @swagger_auto_schema(request_body=SysInterruptDeploymentSLZ, tags=["部署相关接口"])
    def interrupt(self, request, code, module_name, uuid):
        """应用态中断部署，只允许操作调用方管理的应用。

        与用户态中断不同，这里不要求 operator 是部署发起人，operator 只记作操作人。
        接口成功只代表中断请求已受理，最终以部署结果的 interrupted 状态为准。
        """
        deployment = get_module_deployment(self.get_managed_module_via_path(), uuid)
        # 路径里没有环境，按部署所在环境校验，避免 AppSpark 中断用户在预发布环境手动发起的部署
        self.ensure_env_allowed_for_client(deployment.app_environment.environment)

        serializer = SysInterruptDeploymentSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, serializer.data["operator"]))

        try:
            interrupt_deployment(deployment, operator)
        except DeployInterruptionFailed as e:
            raise error_codes.DEPLOY_INTERRUPTION_FAILED.f(str(e))

        # 部署记录里的操作人是部署发起人，应用态中断可能由别人发起，所以单独留一条审计记录
        env = deployment.app_environment
        add_app_audit_record(
            app_code=env.application.code,
            tenant_id=env.application.tenant_id,
            user=operator.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.INTERRUPT_DEPLOY,
            target=OperationTarget.APP,
            module_name=env.module.name,
            environment=env.environment,
            access_type=AccessType.API,
            data_after=DataDetail(data={"deployment_id": str(deployment.id)}),
        )
        return Response({})


class SysOfflineViewSet(OfflineMixin, viewsets.ViewSet, SysManagedAppInPathMixin):
    """应用态下架接口：AIDEV 只能操作 AI Agent 应用，AppSpark 只能操作 AppSpark 应用。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.DEPLOY_APPLICATIONS)]

    @swagger_auto_schema(
        request_body=SysCreateOfflineOperationSLZ,
        tags=["部署相关接口"],
        operation_description="提供给 AIDEV / AppSpark 使用的应用态下架接口，只能操作调用方管理的应用",
    )
    def offline(self, request, code, module_name, environment):
        """应用态发起下架，只允许操作调用方管理的应用，AppSpark 只能下架生产环境。"""
        env = self.get_managed_env_via_path()

        serializer = SysCreateOfflineOperationSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        # operator 仅用于记录操作人，不做 IAM 角色校验：AIDEV 将用户加入应用成员后，IAM 权限存在生效延迟
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, serializer.data["operator"]))
        offline_operation = self.do_offline(env, operator)
        return JsonResponse(data={"offline_operation_id": offline_operation.id}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={200: OfflineOperationSLZ}, tags=["部署相关接口"])
    def get_offline_result(self, request, code, module_name, uuid):
        """应用态查询下架任务结果，只允许查询调用方管理的应用。"""
        offline_operation = self.get_offline_operation(self.get_managed_module_via_path(), uuid)
        self.ensure_env_allowed_for_client(offline_operation.app_environment.environment)
        return JsonResponse(OfflineOperationSLZ(instance=offline_operation).data)
