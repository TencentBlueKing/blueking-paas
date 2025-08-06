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

import copy
import logging

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.cloudapi import serializers
from paasng.accessories.cloudapi.components.bk_apigateway_inner import bk_apigateway_inner_component
from paasng.accessories.cloudapi.utils import get_user_auth_type
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.utils.dictx import get_items
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class CloudAPIViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_CLOUD_API)]

    @swagger_auto_schema(
        response_serializer=serializers.APIGWAPISLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_apis(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_resource_permissions(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        request_body=serializers.APIGWPermissionApplySLZ,
        tags=["CloudAPI"],
    )
    def apply(self, request, *args, **kwargs):
        slz = serializers.APIGWPermissionApplySLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        operation_type = OperationEnum.APPLY
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._post(request, apigw_url, operation_type, app)

    @swagger_auto_schema(
        request_body=serializers.APIGWPermissionBatchApplySLZ,
        tags=["CloudAPI"],
    )
    def batch_apply(self, request, *args, **kwargs):
        slz = serializers.APIGWPermissionBatchApplySLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        operation_type = OperationEnum.APPLY
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._post(request, apigw_url, operation_type, app)

    @swagger_auto_schema(
        request_body=serializers.APIGWPermissionRenewSLZ,
        tags=["CloudAPI"],
    )
    def renew(self, request, *args, **kwargs):
        slz = serializers.APIGWPermissionRenewSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        operation_type = OperationEnum.RENEW
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._post(request, apigw_url, operation_type, app)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWAllowApplyByAPISLZ,
        tags=["CloudAPI"],
    )
    def allow_apply_by_api(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_app_resource_permissions(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        query_serializer=serializers.APIGWPermissionApplyRecordQuerySLZ,
        response_serializer=serializers.APIGWPermissionApplyRecordSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_resource_permission_apply_records(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionApplyRecordDetailSLZ,
        tags=["CloudAPI"],
    )
    def retrieve_resource_permission_apply_record(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        response_serializer=serializers.ESBSystemSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_esb_systems(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_component_permissions(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        request_body=serializers.ESBPermissionApplySLZ,
        tags=["CloudAPI"],
    )
    def apply_component_permissions(self, request, *args, **kwargs):
        slz = serializers.ESBPermissionApplySLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        operation_type = OperationEnum.APPLY
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._post(request, apigw_url, operation_type, app, DataType.ESB_API_RECORD)

    @swagger_auto_schema(
        request_body=serializers.ESBPermissionRenewSLZ,
        tags=["CloudAPI"],
    )
    def renew_component_permissions(self, request, *args, **kwargs):
        slz = serializers.ESBPermissionRenewSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        app = self.get_application()
        operation_type = OperationEnum.RENEW
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._post(request, apigw_url, operation_type, app, DataType.ESB_API_RECORD)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_app_component_permissions(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        query_serializer=serializers.APIGWPermissionApplyRecordQuerySLZ,
        response_serializer=serializers.APIGWPermissionApplyRecordSLZ(many=True),
        tags=["CloudAPI"],
    )
    def list_component_permission_apply_records(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    @swagger_auto_schema(
        response_serializer=serializers.ESBPermissionApplyRecordDetailSLZ,
        tags=["CloudAPI"],
    )
    def retrieve_component_permission_apply_record(self, request, *args, **kwargs):
        app = self.get_application()
        apigw_url = self._trans_request_path_to_apigw_url(request.path, app.code)
        return self._get(request, apigw_url, app)

    def _get(self, request, apigw_url: str, app: Application):
        logger.debug("[cloudapi] getting %s", apigw_url)
        params = copy.copy(request.query_params)
        params.update(
            {
                "target_app_code": app.code,
                "user_auth_type": get_user_auth_type(app.region),
            }
        )
        tenant_id = get_tenant_id_for_app(app.code)
        result = bk_apigateway_inner_component.get(
            apigw_url, params=params, tenant_id=tenant_id, bk_username=request.user.username
        )
        return Response(result)

    def _post(
        self,
        request,
        apigw_url: str,
        operation_type: str,
        app: Application,
        data_type: DataType = DataType.CLOUD_API_RECORD,
    ):
        """
        申请/续期网关/组件 API 权限

        @param: apigw_url: 请求 API 路径
        @param: operation_type: 操作的类型，如申请、续期
        @param: app: 应用
        @param: data_type: 操作前后数据中记录数据的类型，如网关、组件。通过 record_id 获取申请详情时，需要结合 data_type 来调用不同的 API，以获取单据详情
        """
        logger.debug("[cloudapi] posting %s", apigw_url)
        data = copy.copy(request.data)
        data.update(
            {
                "target_app_code": app.code,
                "user_auth_type": get_user_auth_type(app.region),
            }
        )
        tenant_id = get_tenant_id_for_app(app.code)
        result = bk_apigateway_inner_component.post(
            apigw_url, json=data, tenant_id=tenant_id, bk_username=request.user.username
        )

        try:
            # 云 API 申请记录 ID，用于操作详情的展示
            record_id = get_items(result, ["data", "record_id"], "")
            # 仅申请的时候才有 record_id，续期的时候没有
            data_after = DataDetail(type=data_type, data=record_id) if record_id else None

            gateway_name = data.get("gateway_name", "")
            add_app_audit_record(
                app_code=app.code,
                tenant_id=tenant_id,
                user=request.user.pk,
                action_id=AppAction.MANAGE_CLOUD_API,
                operation=operation_type,
                target=OperationTarget.CLOUD_API,
                attribute=gateway_name,
                result_code=ResultCode.SUCCESS,
                data_after=data_after,
            )
        except Exception:
            logger.exception("An exception occurred in the operation record of adding cloud API permissions")
        return Response(result)

    @staticmethod
    def _trans_request_path_to_apigw_url(
        path: str,
        app_code: str,
    ) -> str:
        """将请求路径转换为 bk-apigateway-inner 接口地址"""
        # 请求 bk-apigateway-inner 接口时，约定 `/api/cloudapi/apps/{app_code}/{apigw_url_part}` 为 bk-paas-ng 的 url 前缀，
        # `/api/v1/{apigw_url_part}` 即为 bk-apigateway-inner 接口地址
        force_script_name = getattr(settings, "FORCE_SCRIPT_NAME", "") or ""
        prefix = f"{force_script_name}/api/cloudapi/apps/{app_code}/"
        if path.startswith(prefix):
            return f"/api/v1/{path[len(prefix):]}"

        raise error_codes.CLOUDAPI_PATH_ERROR
