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

from django.db.models import Count
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.core.tenant.constants import AppTenantMode
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.applications.serializers.application import (
    ApplicationDetailSLZ,
    ApplicationSLZ,
    ApplicationTypeListSLZ,
    TenantIdListSLZ,
    TenantModeListSLZ,
)
from paasng.plat_mgt.applications.utils.filters import ApplicationFilterBackend
from paasng.plat_mgt.applications.utils.pagination import ApplicationListPagination
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application


class ApplicationView(viewsets.GenericViewSet):
    """平台管理 - 应用列表 API"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [ApplicationFilterBackend]
    pagination_class = ApplicationListPagination

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用列表",
        responses={status.HTTP_200_OK: ApplicationSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取应用列表"""

        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        slz = ApplicationSLZ(page, many=True, context={"request": request})
        return self.get_paginated_response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取单个应用信息",
        responses={status.HTTP_200_OK: ApplicationDetailSLZ()},
    )
    def retrieve(self, request, *args, **kwargs):
        """获取单个应用信息"""
        app_code = kwargs.get("app_code")
        app = self.get_queryset().filter(code=app_code).first()
        if not app:
            return Response({"detail": "Application not found"}, status=status.HTTP_404_NOT_FOUND)

        slz = ApplicationDetailSLZ(app)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用租户类型列表",
        responses={status.HTTP_200_OK: TenantIdListSLZ(many=True)},
    )
    def list_tenant_id(self, request, *args, **kwargs):
        """获取数据库中各租户的应用数量"""
        tenant_id_list = []
        # 查询全租户可用的应用
        global_apps = self.get_queryset().filter(app_tenant_mode=AppTenantMode.GLOBAL.value)
        tenant_id_list.append(
            {
                "tenant_id": AppTenantMode.GLOBAL.value,
                "app_count": global_apps.count(),
            }
        )
        # 查询各个租户的应用数量
        tenant_id_counts = (
            self.get_queryset()
            .filter(app_tenant_mode=AppTenantMode.SINGLE.value)
            .values("app_tenant_id")
            .annotate(app_count=Count("id"))
            .order_by("app_tenant_id")
        )
        for tenant in tenant_id_counts:
            tenant_id_list.append(
                {
                    "tenant_id": tenant["app_tenant_id"],
                    "app_count": tenant["app_count"],
                }
            )
        slz = TenantIdListSLZ(tenant_id_list, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用租户模式列表",
        responses={status.HTTP_200_OK: TenantModeListSLZ(many=True)},
    )
    def list_tenant_mode(self, request, *args, **kwargs):
        """获取应用租户模式列表"""
        tenant_modes = []
        for enum_mode in AppTenantMode:
            tenant_modes.append(
                {"type": enum_mode[0], "label": enum_mode[1]},
            )
        slz = TenantModeListSLZ(tenant_modes, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用类型列表",
        responses={status.HTTP_200_OK: ApplicationTypeListSLZ(many=True)},
    )
    def list_app_types(self, request):
        """获取应用类型列表"""
        app_types = []
        for enum_type in ApplicationType:
            app_types.append(
                {"type": enum_type[0], "label": enum_type[1]},
            )
        slz = ApplicationTypeListSLZ(app_types, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)
