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

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from paasng.plat_mgt.applications import serializers as slzs
from paasng.platform.applications.models import Application


class ApplicationFilterBackend(BaseFilterBackend):
    """Application filter backend"""

    def filter_queryset(self, request, queryset, view):
        if queryset.model != Application:
            raise ValueError("ApplicationFilterBackend only support to filter Application")

        slz = slzs.ApplicationListFilterInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        validate_params = slz.data

        # 搜索应用 名称/ID 过滤
        search = validate_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))

        # 应用名称过滤
        name = validate_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)

        # 应用租户ID过滤
        tenant_id = validate_params.get("tenant_id")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # 应用租户模式过滤
        app_tenant_mode = validate_params.get("app_tenant_mode")
        if app_tenant_mode:
            queryset = queryset.filter(app_tenant_mode=app_tenant_mode)

        # 应用类型过滤
        app_type = validate_params.get("type")
        if app_type:
            queryset = queryset.filter(type=app_type)

        # 应用激活状态过滤
        is_active = validate_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        # 处理排序
        ## 已下架的应用永远排在最后
        order_by = ["-is_active"] + (validate_params.get("order_by") or [])
        queryset = queryset.order_by(*order_by)

        return queryset
