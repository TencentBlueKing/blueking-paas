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
import copy
import logging

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.dev_resources.cloudapi import serializers
from paasng.dev_resources.cloudapi.components.apigw_dashboard import apigw_dashboard_component
from paasng.dev_resources.cloudapi.utils import get_user_auth_type
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.operations.constant import OperationType
from paasng.platform.operations.models import Operation
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class CloudAPIViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.MANAGE_CLOUD_API)]

    @swagger_auto_schema(
        response_serializer=serializers.APIGWAPISLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_apis(self, request, app_code: str, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_resource_permissions(self, request, app_code: str, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        request_body=serializers.APIGWPermissionApplySLZ,
        tags=['CloudAPI'],
    )
    def apply(self, request, app_code: str, *args, **kwargs):
        slz = serializers.APIGWPermissionApplySLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        operation_type = OperationType.APPLY_PERM_FOR_CLOUD_API.value
        return self._post(request, operation_type, app_code, *args, **kwargs)

    @swagger_auto_schema(
        request_body=serializers.APIGWPermissionRenewSLZ,
        tags=['CloudAPI'],
    )
    def renew(self, request, app_code: str, *args, **kwargs):
        slz = serializers.APIGWPermissionRenewSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        operation_type = OperationType.RENEW_PERM_FOR_CLOUD_API.value
        return self._post(request, operation_type, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWAllowApplyByAPISLZ,
        tags=['CloudAPI'],
    )
    def allow_apply_by_api(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_app_resource_permissions(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        query_serializer=serializers.APIGWPermissionApplyRecordQuerySLZ,
        response_serializer=serializers.APIGWPermissionApplyRecordSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_resource_permission_apply_records(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionApplyRecordDetailSLZ,
        tags=['CloudAPI'],
    )
    def retrieve_resource_permission_apply_record(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.ESBSystemSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_esb_systems(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_component_permissions(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        request_body=serializers.ESBPermissionApplySLZ,
        tags=['CloudAPI'],
    )
    def apply_component_permissions(self, request, app_code, *args, **kwargs):
        slz = serializers.ESBPermissionApplySLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        operation_type = OperationType.APPLY_PERM_FOR_CLOUD_API.value
        return self._post(request, operation_type, app_code, *args, **kwargs)

    @swagger_auto_schema(
        request_body=serializers.ESBPermissionRenewSLZ,
        tags=['CloudAPI'],
    )
    def renew_component_permissions(self, request, app_code, *args, **kwargs):
        slz = serializers.ESBPermissionRenewSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        operation_type = OperationType.RENEW_PERM_FOR_CLOUD_API.value
        return self._post(request, operation_type, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.APIGWPermissionSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_app_component_permissions(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        query_serializer=serializers.APIGWPermissionApplyRecordQuerySLZ,
        response_serializer=serializers.APIGWPermissionApplyRecordSLZ(many=True),
        tags=['CloudAPI'],
    )
    def list_component_permission_apply_records(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    @swagger_auto_schema(
        response_serializer=serializers.ESBPermissionApplyRecordDetailSLZ,
        tags=['CloudAPI'],
    )
    def retrieve_component_permission_apply_record(self, request, app_code, *args, **kwargs):
        return self._get(request, app_code, *args, **kwargs)

    def _get(self, request, app_code: str, *args, **kwargs):
        logger.debug("[cloudapi] getting %s", self._get_apigw_dashboard_path(request.path, app_code))
        params = copy.copy(request.query_params)
        params.update(
            {
                'target_app_code': app_code,
                'user_auth_type': get_user_auth_type(self._get_app_region()),
            }
        )

        result = apigw_dashboard_component.get(
            self._get_apigw_dashboard_path(request.path, app_code),
            params=params,
            bk_username=request.user.username,
        )
        return Response(result)

    def _post(self, request, operation_type: int, app_code: str, *args, **kwargs):
        logger.debug("[cloudapi] posting %s", self._get_apigw_dashboard_path(request.path, app_code))
        data = copy.copy(request.data)
        data.update(
            {
                'target_app_code': app_code,
                'user_auth_type': get_user_auth_type(self._get_app_region()),
            }
        )

        result = apigw_dashboard_component.post(
            self._get_apigw_dashboard_path(request.path, app_code),
            json=data,
            bk_username=request.user.username,
        )

        # 记录操作记录
        try:
            # 部分 API 没有带上网关名，则不记录到操作记录中
            gateway_name = data.get('gateway_name')
            if gateway_name:
                application = self.get_application()
                Operation.objects.create(
                    region=application.region,
                    application=application,
                    type=operation_type,
                    user=request.user,
                    extra_values={"gateway_name": gateway_name},
                )
        except Exception:
            logger.exception("An exception occurred in the operation record of adding cloud API permissions")

        return Response(result)

    def _get_apigw_dashboard_path(self, path: str, app_code: str) -> str:
        # 请求 apigw-dashboard 接口时，约定 `/api/cloudapi/apps/{app_code}/` 为 bk-paas-ng 的 url 前缀，
        # `/api/v1/` + `其他部分` 即为 apigw-dashboard 接口地址
        prefix = self._get_request_path_prefix(path, app_code)
        if path.startswith(prefix):
            return f'/api/v1/{path[len(prefix):]}'

        raise error_codes.CLOUDAPI_PATH_ERROR

    def _get_request_path_prefix(self, path: str, app_code: str) -> str:
        force_script_name = getattr(settings, 'FORCE_SCRIPT_NAME', '') or ''
        return f'{force_script_name}/api/cloudapi/apps/{app_code}/'

    def _get_app_region(self) -> str:
        app = self.get_application()
        return app.region
