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

from paasng.platform.applications.models import Application


class ApplicationFilterBackend(BaseFilterBackend):
    """Application filter backend"""

    def filter_queryset(self, request, queryset, view):
        if queryset.model != Application:
            raise ValueError("ApplicationFilterBackend only support to filter Application")

        # 标签过滤 - system, tenant, tenant2
        app_tenant_id = request.query_params.get("app_tenant_id", None)
        if app_tenant_id:
            queryset = queryset.filter(app_tenant_id=app_tenant_id)

        # 关键字过滤 - 名称/ID 搜索
        search = request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))

        # 专门的应用名称过滤
        app_name = request.query_params.get("name")
        if app_name:
            queryset = queryset.filter(name__icontains=app_name)

        # 租户类型过滤
        app_tenant_mode = request.query_params.get("app_tenant_mode")
        if app_tenant_mode:
            queryset = queryset.filter(app_tenant_mode=app_tenant_mode)

        # 应用类型过滤
        type = request.query_params.get("type")
        if type:
            queryset = queryset.filter(type=type)

        # 状态过滤
        status = request.query_params.get("is_active")
        if status is not None:
            queryset = queryset.filter(is_active=status.lower() == "true")

        # 排序操作
        ordering = request.query_params.get("ordering")
        if ordering:
            # 支持多个字段排序, 用逗号分隔
            # 字段前添加 '-' 表示降序
            order_fields = ordering.split(",")
            queryset = queryset.order_by(*order_fields)
        else:
            queryset = queryset.order_by("-created")

        return queryset
