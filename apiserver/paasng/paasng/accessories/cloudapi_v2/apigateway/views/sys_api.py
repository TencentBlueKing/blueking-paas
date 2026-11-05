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

"""网关 API 的应用态 (系统 API) 视图"""

import logging

from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.response import Response

from paasng.accessories.cloudapi_v2.apigateway import serializers
from paasng.accessories.cloudapi_v2.apigateway.clients import ApiGatewayClient
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import AccessType, DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.dictx import get_items

logger = logging.getLogger(__name__)


class SysGatewayAPIViewSet(viewsets.ViewSet, SysManagedAppInPathMixin):
    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_CLOUD_API)]

    @swagger_auto_schema(
        query_serializer=serializers.ListGatewaysInputSLZ,
        responses={200: serializers.ListGatewaysOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_gateways(self, request, code, *args, **kwargs):
        """获取网关列表"""
        slz = serializers.ListGatewaysInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        data = ApiGatewayClient(tenant_id=tenant_id).list_gateways(**slz.validated_data)
        return Response(serializers.ListGatewaysOutputSLZ(data, many=True).data)

    @swagger_auto_schema(
        query_serializer=serializers.ListGatewayPermissionResourcesInputSLZ,
        responses={200: serializers.ListGatewayPermissionResourcesOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_gateway_permission_resources(self, request, code, gateway_name, *args, **kwargs):
        """获取网关资源列表"""
        slz = serializers.ListGatewayPermissionResourcesInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        data = ApiGatewayClient(tenant_id=tenant_id).list_gateway_permission_resources(
            app_code=app.code, gateway_name=gateway_name, **slz.validated_data
        )
        return Response(serializers.ListGatewayPermissionResourcesOutputSLZ(data, many=True).data)

    @swagger_auto_schema(
        request_body=serializers.SysApplyGatewayResourcePermissionInputSLZ,
        responses={200: serializers.ApplyGatewayResourcePermissionOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def apply_gateway_resource_permission(self, request, code, gateway_name, *args, **kwargs):
        """网关资源权限申请"""
        slz = serializers.SysApplyGatewayResourcePermissionInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data
        operator = params.pop("operator")

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        result = ApiGatewayClient(tenant_id=tenant_id, bk_username=operator).apply_gateway_resource_permission(
            app_code=app.code, gateway_name=gateway_name, **params
        )

        # 记录审计日志
        try:
            record_id = get_items(result, ["record_id"], "")
            data_after = DataDetail(type=DataType.CLOUD_API_RECORD, data=record_id) if record_id else None

            add_app_audit_record(
                app_code=app.code,
                tenant_id=tenant_id,
                user=user_id_encoder.encode(settings.USER_TYPE, operator),
                action_id=AppAction.MANAGE_CLOUD_API,
                operation=OperationEnum.APPLY,
                target=OperationTarget.CLOUD_API,
                attribute=gateway_name,
                access_type=AccessType.API,
                result_code=ResultCode.SUCCESS,
                data_after=data_after,
            )
        except Exception:
            logger.exception("Failed to add audit record for apply gateway resource permission")

        return Response(serializers.ApplyGatewayResourcePermissionOutputSLZ(result).data)

    @swagger_auto_schema(
        query_serializer=serializers.ListResourcePermissionApplyRecordsInputSLZ,
        responses={200: serializers.PaginatedPermissionApplyRecordOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def list_resource_permission_apply_records(self, request, code, *args, **kwargs):
        """资源权限申请记录列表"""
        slz = serializers.ListResourcePermissionApplyRecordsInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        app = self.get_managed_application_via_path()
        tenant_id = get_tenant_id_for_app(app.code)
        data = ApiGatewayClient(tenant_id=tenant_id).list_resource_permission_apply_records(
            app_code=app.code, **slz.validated_data
        )
        return Response(serializers.PaginatedPermissionApplyRecordOutputSLZ(data).data)
