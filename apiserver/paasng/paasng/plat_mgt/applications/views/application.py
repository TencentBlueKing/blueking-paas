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

from collections import Counter

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.core.core.storages.redisdb import DefaultRediStore
from paasng.core.tenant.constants import AppTenantMode
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.applications import serializers as slzs
from paasng.plat_mgt.applications.utils.filters import ApplicationFilterBackend
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.applications.tasks import cal_app_resource_quotas


class ApplicationListViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用列表 API"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [ApplicationFilterBackend]
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用列表",
        responses={status.HTTP_200_OK: slzs.ApplicationListSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取应用列表"""
        queryset = self.get_queryset()
        filter_queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(filter_queryset)
        app_resource_quotas = self.get_app_resource_quotas()

        slz = slzs.ApplicationListSLZ(
            page,
            many=True,
            context={"request": request, "app_resource_quotas": app_resource_quotas},
        )
        return self.get_paginated_response(slz.data)

    def get_app_resource_quotas(self) -> dict:
        """获取应用资源配额信息，优先从 Redis 缓存获取，缺失时触发异步任务计算"""
        # 尝试从 Redis 中获取资源配额
        store = DefaultRediStore(rkey="quotas::app")
        app_resource_quotas = store.get()

        if not app_resource_quotas:
            # 触发异步任务计算资源配额
            # 计算完成后会将结果存入 Redis 中
            cal_app_resource_quotas.delay()

        return app_resource_quotas or {}

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取各租户的应用数量",
        responses={status.HTTP_200_OK: slzs.TenantAppStatisticsSLZ(many=True)},
    )
    def list_tenant_app_statistics(self, request):
        """获取各租户的应用数量"""
        # 应用所有过滤条件, 获取过滤后的查询集
        filtered_queryset = self.filter_queryset(self.get_queryset())

        tenant_id_list = []
        # 查询全租户可用的应用
        global_apps = filtered_queryset.filter(app_tenant_mode=AppTenantMode.GLOBAL.value)
        tenant_id_list.append(
            {
                "tenant_id": AppTenantMode.GLOBAL.value,
                "app_count": global_apps.count(),
            }
        )
        # 查询各个租户的应用数量
        tenant_ids = filtered_queryset.filter(app_tenant_mode=AppTenantMode.SINGLE.value).values_list(
            "app_tenant_id", flat=True
        )
        tenant_id_counts = Counter(tenant_ids)
        for tenant_id in sorted(tenant_id_counts.keys()):
            tenant_id_list.append({"tenant_id": tenant_id, "app_count": tenant_id_counts[tenant_id]})
        slz = slzs.TenantAppStatisticsSLZ(tenant_id_list, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用租户模式类型列表",
        responses={status.HTTP_200_OK: slzs.TenantModeSLZ(many=True)},
    )
    def list_tenant_modes(self, request, *args, **kwargs):
        """获取应用租户模式类型列表"""
        tenant_modes = [{"type": type, "label": label} for type, label in AppTenantMode.get_choices()]
        slz = slzs.TenantModeSLZ(tenant_modes, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用类型列表",
        responses={status.HTTP_200_OK: slzs.ApplicationTypeSLZ(many=True)},
    )
    def list_app_types(self, request):
        """获取应用类型列表"""
        app_types = [{"type": type, "label": label} for type, label in ApplicationType.get_choices()]
        slz = slzs.ApplicationTypeSLZ(app_types, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)
