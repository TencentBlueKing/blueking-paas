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

"""应用态 (系统 API) Agent Sandbox 视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV 等固定的系统调用, 鉴权依赖 sysapi_client.
"""

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.accessories.cloudapi_v2.apigateway.clients import ApiGatewayClient
from paasng.accessories.cloudapi_v2.apigateway.exceptions import ApiGatewayServiceError
from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.agent_sandbox.serializers import GrantAgentSandboxPermissionSLZ
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.error_codes import error_codes


@ForceAllowAuthedApp.mark_view_set
class AgentSandboxAPIPermissionViewSet(viewsets.ViewSet):
    """Agent Sandbox API 权限管理相关接口。

    AIDev 平台通过该接口为指定的 AI Agent 应用授予 Agent Sandbox 相关 API 的调用权限。
    授权完成后，该应用即可通过开发者中心提供的网关接口，访问沙箱的创建、删除、文件操作、进程管理及日志查看等接口。
    """

    permission_classes = [sysapi_client_perm_class(ClientAction.GRANT_APIGW_PERMISSIONS)]

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=GrantAgentSandboxPermissionSLZ(),
        responses={status.HTTP_201_CREATED: ""},
    )
    def grant_permissions(self, request):
        """为指定的 AI Agent 应用授予 Agent Sandbox 相关 API 的调用权限。"""
        slz = GrantAgentSandboxPermissionSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        target_app_code = validated_data["target_app_code"]
        expire_days = validated_data["expire_days"]

        tenant_id = get_tenant_id_for_app(target_app_code)
        try:
            client = ApiGatewayClient(tenant_id=tenant_id)
            client.grant_apigw_permissions(
                gateway_name=settings.APIGW_GRANT_GATEWAY_NAME,
                target_app_code=target_app_code,
                resource_names=settings.APIGW_GRANT_AGENT_SANDBOX_APIS,
                expire_days=expire_days,
            )
        except ApiGatewayServiceError as e:
            raise error_codes.REMOTE_REQUEST_ERROR.f(str(e))

        return Response(status=status.HTTP_201_CREATED)
