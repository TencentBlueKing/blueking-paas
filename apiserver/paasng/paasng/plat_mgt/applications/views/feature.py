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


from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.applications import serializers as slzs
from paasng.platform.applications.models import Application, ApplicationFeatureFlag


class ApplicationFeatureViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用特性 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用列表",
        responses={status.HTTP_200_OK: slzs.ApplicationFeatureFlagListOutputSLZ(many=True)},
    )
    def list(self, request, app_code):
        """获取指定应用的列表"""
        application = get_object_or_404(Application, code=app_code)
        application_features = ApplicationFeatureFlag.objects.get_application_features(application=application)
        slz = slzs.ApplicationFeatureFlagListOutputSLZ(
            [{"name": key, "effect": value} for key, value in application_features.items()], many=True
        )
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="更新应用特性",
        request_body=slzs.ApplicationFeatureFlagUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, app_code):
        """更新应用特性"""
        application = get_object_or_404(Application, code=app_code)
        slz = slzs.ApplicationFeatureFlagUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 创建或更新应用特性
        name, effect = data["name"], data["effect"]
        data_before = DataDetail(data=application.feature_flag.get_application_features())
        application.feature_flag.set_feature(name, effect)

        operation = OperationEnum.ENABLE if effect else OperationEnum.DISABLE

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=operation,
            target=OperationTarget.FEATURE_FLAG,
            app_code=application.code,
            data_before=data_before,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
