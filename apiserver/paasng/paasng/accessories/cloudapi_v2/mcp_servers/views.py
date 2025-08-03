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

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.cloudapi_v2 import serializers
from paasng.accessories.cloudapi_v2.mcp_servers.clients import MCPServerApiClient
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.tenant import get_tenant_id_for_app

logger = logging.getLogger(__name__)


class MCPServerAPIViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_CLOUD_API)]

    @swagger_auto_schema(
        query_serializer=serializers.MCPServerQueryParamsSLZ,
        tags=["CloudAPIV2"],
    )
    def list_mcp_servers(self, request, *args, **kwargs):
        slz = serializers.MCPServerQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        tenant_id = get_tenant_id_for_app(app.code)
        data = MCPServerApiClient(tenant_id=tenant_id).list_app_mcp_servers(app_code=app.code, **slz.validated_data)
        return Response(data)

    @swagger_auto_schema(tags=["CloudAPIV2"])
    def list_app_mcp_server_permissions(self, request, *args, **kwargs):
        app = self.get_application()
        tenant_id = get_tenant_id_for_app(app.code)
        data = MCPServerApiClient(tenant_id=tenant_id).list_app_permissions(app_code=app.code)
        return Response(data)

    @swagger_auto_schema(
        query_serializer=serializers.AppMCPServerPermissionApplyRecordQueryParamsSLZ,
        tags=["CloudAPIV2"],
    )
    def list_mcp_server_permissions_apply_records(self, request, *args, **kwargs):
        slz = serializers.AppMCPServerPermissionApplyRecordQueryParamsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        tenant_id = get_tenant_id_for_app(app.code)
        data = MCPServerApiClient(tenant_id=tenant_id).list_permissions_apply_records(
            app_code=app.code, **slz.validated_data
        )
        return Response(data)

    @swagger_auto_schema(
        request_body=serializers.ApplyMCPResourcePermissionInputSLZ,
        tags=["CloudAPIV2"],
    )
    def apply_mcp_server_permissions(self, request, *args, **kwargs):
        slz = serializers.ApplyMCPResourcePermissionInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        app = self.get_application()
        tenant_id = get_tenant_id_for_app(app.code)
        MCPServerApiClient(tenant_id=tenant_id).apply_permissions(app_code=app.code, **data)

        # 云 API 申请记录 ID，用于操作详情的展示
        data_after = DataDetail(type=DataType.CLOUD_API_RECORD, data=data)

        add_app_audit_record(
            app_code=app.code,
            tenant_id=tenant_id,
            user=request.user.pk,
            action_id=AppAction.MANAGE_CLOUD_API,
            operation=OperationEnum.APPLY,
            target=OperationTarget.CLOUD_API,
            result_code=ResultCode.SUCCESS,
            data_after=data_after,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
