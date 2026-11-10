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

"""MCP Server 的应用态 (系统 API) 视图"""

import logging

from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.accessories.cloudapi_v2 import serializers
from paasng.accessories.cloudapi_v2.mcp_servers.clients import MCPServerApiClient
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import AccessType, DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.platform.applications.tenant import get_tenant_id_for_app

logger = logging.getLogger(__name__)


class SysMCPServerAPIViewSet(viewsets.ViewSet, SysManagedAppInPathMixin):
    """应用态 MCP Server 接口: MCP 列表、权限申请、申请状态查询"""

    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_CLOUD_API)]

    @swagger_auto_schema(
        query_serializer=serializers.MCPServerQueryParamsSLZ,
        tags=["CloudAPIV2"],
    )
    def list_mcp_servers(self, request, code, *args, **kwargs):
        slz = serializers.MCPServerQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        data = MCPServerApiClient(tenant_id=tenant_id).list_app_mcp_servers(app_code=app.code, **slz.validated_data)
        return Response(data)

    @swagger_auto_schema(
        request_body=serializers.SysApplyMCPResourcePermissionInputSLZ,
        tags=["CloudAPIV2"],
    )
    def apply_mcp_server_permissions(self, request, code, *args, **kwargs):
        slz = serializers.SysApplyMCPResourcePermissionInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        operator = params.pop("operator")

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        MCPServerApiClient(tenant_id=tenant_id).apply_permissions(app_code=app.code, **params)

        # 记录审计日志
        try:
            add_app_audit_record(
                app_code=app.code,
                tenant_id=tenant_id,
                user=user_id_encoder.encode(settings.USER_TYPE, operator),
                action_id=AppAction.MANAGE_CLOUD_API,
                operation=OperationEnum.APPLY,
                target=OperationTarget.CLOUD_API,
                access_type=AccessType.API,
                result_code=ResultCode.SUCCESS,
                data_after=DataDetail(type=DataType.CLOUD_API_RECORD, data=params),
            )
        except Exception:
            logger.exception("Failed to add audit record for apply mcp server permissions")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        query_serializer=serializers.AppMCPServerPermissionApplyRecordQueryParamsSLZ,
        tags=["CloudAPIV2"],
    )
    def list_mcp_server_permissions_apply_records(self, request, code, *args, **kwargs):
        slz = serializers.AppMCPServerPermissionApplyRecordQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        data = MCPServerApiClient(tenant_id=tenant_id).list_permissions_apply_records(
            app_code=app.code, **slz.validated_data
        )
        return Response(data)
