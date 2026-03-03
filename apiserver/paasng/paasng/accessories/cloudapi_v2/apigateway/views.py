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

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.cloudapi_v2.apigateway import serializers
from paasng.accessories.cloudapi_v2.apigateway.clients import ApiGatewayClient
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.dictx import get_items

logger = logging.getLogger(__name__)


class GatewayAPIViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """网关 API 权限管理"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_CLOUD_API)]

    def _get_app_and_tenant(self):
        app = self.get_application()
        tenant_id = get_tenant_id_for_app(app.code)
        return app, tenant_id

    def _get_client(self, tenant_id, request):
        return ApiGatewayClient(tenant_id=tenant_id, bk_username=request.user.username)

    def _validate(self, slz_cls, *, data):
        slz = slz_cls(data=data)
        slz.is_valid(raise_exception=True)
        return slz.validated_data

    def _response_with_serializer(self, slz_cls, data, *, many=False):
        out_slz = slz_cls(data, many=many)
        return Response(out_slz.data)

    @swagger_auto_schema(
        query_serializer=serializers.ListGatewaysInputSLZ,
        responses={200: serializers.ListGatewaysOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_gateways(self, request, *args, **kwargs):
        """获取网关列表"""
        validated_data = self._validate(serializers.ListGatewaysInputSLZ, data=request.query_params)

        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_gateways(**validated_data)
        return self._response_with_serializer(serializers.ListGatewaysOutputSLZ, data, many=True)

    @swagger_auto_schema(
        responses={200: serializers.GetGatewayOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def get_gateway(self, request, gateway_name: str, *args, **kwargs):
        """获取单个网关详情"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).get_gateway(gateway_name=gateway_name)
        return self._response_with_serializer(serializers.GetGatewayOutputSLZ, data)

    @swagger_auto_schema(
        query_serializer=serializers.ListGatewayPermissionResourcesInputSLZ,
        responses={200: serializers.ListGatewayPermissionResourcesOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_gateway_permission_resources(self, request, gateway_name: str, *args, **kwargs):
        """获取网关资源列表（权限申请用）"""
        validated_data = self._validate(serializers.ListGatewayPermissionResourcesInputSLZ, data=request.query_params)

        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_gateway_permission_resources(
            app_code=app.code, gateway_name=gateway_name, **validated_data
        )
        return self._response_with_serializer(serializers.ListGatewayPermissionResourcesOutputSLZ, data, many=True)

    @swagger_auto_schema(
        responses={200: serializers.CheckIsAllowedApplyByGatewayOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def check_is_allowed_apply_by_gateway(self, request, gateway_name: str, *args, **kwargs):
        """是否允许按网关申请资源权限"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).check_is_allowed_apply_by_gateway(
            app_code=app.code, gateway_name=gateway_name
        )
        return self._response_with_serializer(serializers.CheckIsAllowedApplyByGatewayOutputSLZ, data)

    @swagger_auto_schema(
        request_body=serializers.ApplyGatewayResourcePermissionInputSLZ,
        responses={200: serializers.ApplyGatewayResourcePermissionOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def apply_gateway_resource_permission(self, request, gateway_name: str, *args, **kwargs):
        """网关资源权限申请"""
        validated_data = self._validate(serializers.ApplyGatewayResourcePermissionInputSLZ, data=request.data)

        app, tenant_id = self._get_app_and_tenant()
        result = self._get_client(tenant_id, request).apply_gateway_resource_permission(
            app_code=app.code, gateway_name=gateway_name, **validated_data
        )

        # 记录审计日志
        try:
            record_id = get_items(result, ["record_id"], "")
            data_after = DataDetail(type=DataType.CLOUD_API_RECORD, data=record_id) if record_id else None

            add_app_audit_record(
                app_code=app.code,
                tenant_id=tenant_id,
                user=request.user.pk,
                action_id=AppAction.MANAGE_CLOUD_API,
                operation=OperationEnum.APPLY,
                target=OperationTarget.CLOUD_API,
                attribute=gateway_name,
                result_code=ResultCode.SUCCESS,
                data_after=data_after,
            )
        except Exception:
            logger.exception("Failed to add audit record for apply gateway resource permission")

        return self._response_with_serializer(serializers.ApplyGatewayResourcePermissionOutputSLZ, result)

    @swagger_auto_schema(
        responses={200: serializers.ListAppResourcePermissionsOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_app_resource_permissions(self, request, *args, **kwargs):
        """已申请的资源权限列表"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_app_resource_permissions(app_code=app.code)
        return self._response_with_serializer(serializers.ListAppResourcePermissionsOutputSLZ, data, many=True)

    @swagger_auto_schema(
        request_body=serializers.RenewResourcePermissionInputSLZ,
        tags=["CloudAPIV2"],
    )
    def renew_resource_permission(self, request, *args, **kwargs):
        """权限续期"""
        validated_data = self._validate(serializers.RenewResourcePermissionInputSLZ, data=request.data)

        app, tenant_id = self._get_app_and_tenant()
        result = self._get_client(tenant_id, request).renew_resource_permission(app_code=app.code, **validated_data)

        # 记录审计日志
        try:
            add_app_audit_record(
                app_code=app.code,
                tenant_id=tenant_id,
                user=request.user.pk,
                action_id=AppAction.MANAGE_CLOUD_API,
                operation=OperationEnum.RENEW,
                target=OperationTarget.CLOUD_API,
                result_code=ResultCode.SUCCESS,
            )
        except Exception:
            logger.exception("Failed to add audit record for renew resource permission")

        return Response(result)

    @swagger_auto_schema(
        query_serializer=serializers.ListResourcePermissionApplyRecordsInputSLZ,
        responses={200: serializers.PaginatedPermissionApplyRecordOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def list_resource_permission_apply_records(self, request, *args, **kwargs):
        """资源权限申请记录列表"""
        validated_data = self._validate(
            serializers.ListResourcePermissionApplyRecordsInputSLZ, data=request.query_params
        )

        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_resource_permission_apply_records(
            app_code=app.code, **validated_data
        )
        return self._response_with_serializer(serializers.PaginatedPermissionApplyRecordOutputSLZ, data)

    @swagger_auto_schema(
        responses={200: serializers.RetrieveResourcePermissionApplyRecordOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def retrieve_resource_permission_apply_record(self, request, record_id: int, *args, **kwargs):
        """资源权限申请记录详情"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).retrieve_resource_permission_apply_record(
            app_code=app.code, record_id=record_id
        )
        return self._response_with_serializer(serializers.RetrieveResourcePermissionApplyRecordOutputSLZ, data)

    @swagger_auto_schema(
        query_serializer=serializers.ListESBSystemsInputSLZ,
        responses={200: serializers.ESBSystemOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_esb_systems(self, request, *args, **kwargs):
        """查询组件系统列表"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_esb_systems(
            user_auth_type=settings.BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE
        )
        return self._response_with_serializer(serializers.ESBSystemOutputSLZ, data, many=True)

    @swagger_auto_schema(
        query_serializer=serializers.ListESBSystemPermissionComponentsInputSLZ,
        responses={200: serializers.ESBComponentOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_esb_system_permission_components(self, request, system_id: int, *args, **kwargs):
        """查询系统权限组件"""
        validated_data = self._validate(
            serializers.ListESBSystemPermissionComponentsInputSLZ, data=request.query_params
        )

        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_esb_system_permission_components(
            app_code=app.code, system_id=system_id, **validated_data
        )
        return self._response_with_serializer(serializers.ESBComponentOutputSLZ, data, many=True)

    @swagger_auto_schema(
        request_body=serializers.ApplyESBSystemComponentPermissionsInputSLZ,
        responses={200: serializers.ApplyESBSystemComponentPermissionsOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def apply_esb_system_component_permissions(self, request, system_id: int, *args, **kwargs):
        """创建申请 ESB 组件权限的申请单据"""
        validated_data = self._validate(serializers.ApplyESBSystemComponentPermissionsInputSLZ, data=request.data)

        app, tenant_id = self._get_app_and_tenant()
        result = self._get_client(tenant_id, request).apply_esb_system_component_permissions(
            app_code=app.code, system_id=system_id, **validated_data
        )

        # 记录审计日志
        try:
            record_id = get_items(result, ["record_id"], "")
            data_after = DataDetail(type=DataType.ESB_API_RECORD, data=record_id) if record_id else None

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
        except Exception:
            logger.exception("Failed to add audit record for apply esb component permissions")

        return self._response_with_serializer(serializers.ApplyESBSystemComponentPermissionsOutputSLZ, result)

    @swagger_auto_schema(
        request_body=serializers.RenewESBComponentPermissionsInputSLZ,
        tags=["CloudAPIV2"],
    )
    def renew_esb_component_permissions(self, request, *args, **kwargs):
        """ESB 组件权限续期"""
        validated_data = self._validate(serializers.RenewESBComponentPermissionsInputSLZ, data=request.data)

        app, tenant_id = self._get_app_and_tenant()
        result = self._get_client(tenant_id, request).renew_esb_component_permissions(
            app_code=app.code, **validated_data
        )

        # 记录审计日志
        try:
            add_app_audit_record(
                app_code=app.code,
                tenant_id=tenant_id,
                user=request.user.pk,
                action_id=AppAction.MANAGE_CLOUD_API,
                operation=OperationEnum.RENEW,
                target=OperationTarget.CLOUD_API,
                result_code=ResultCode.SUCCESS,
            )
        except Exception:
            logger.exception("Failed to add audit record for renew esb component permissions")

        return Response(result)

    @swagger_auto_schema(
        responses={200: serializers.ESBComponentOutputSLZ(many=True)},
        tags=["CloudAPIV2"],
    )
    def list_app_esb_component_permissions(self, request, *args, **kwargs):
        """已申请的 ESB 组件权限列表"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_app_esb_component_permissions(app_code=app.code)
        return self._response_with_serializer(serializers.ESBComponentOutputSLZ, data, many=True)

    @swagger_auto_schema(
        query_serializer=serializers.ListAppESBComponentPermissionApplyRecordsInputSLZ,
        responses={200: serializers.PaginatedESBComponentPermissionApplyRecordOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def list_app_esb_component_permission_apply_records(self, request, *args, **kwargs):
        """查询应用权限申请记录列表"""
        validated_data = self._validate(
            serializers.ListAppESBComponentPermissionApplyRecordsInputSLZ, data=request.query_params
        )

        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).list_app_esb_component_permission_apply_records(
            app_code=app.code, **validated_data
        )
        return self._response_with_serializer(serializers.PaginatedESBComponentPermissionApplyRecordOutputSLZ, data)

    @swagger_auto_schema(
        responses={200: serializers.GetAppESBComponentPermissionApplyRecordOutputSLZ},
        tags=["CloudAPIV2"],
    )
    def get_app_esb_component_permission_apply_record(self, request, record_id: int, *args, **kwargs):
        """查询应用权限申请记录详情"""
        app, tenant_id = self._get_app_and_tenant()
        data = self._get_client(tenant_id, request).get_app_esb_component_permission_apply_record(
            app_code=app.code, record_id=record_id
        )
        return self._response_with_serializer(serializers.GetAppESBComponentPermissionApplyRecordOutputSLZ, data)
