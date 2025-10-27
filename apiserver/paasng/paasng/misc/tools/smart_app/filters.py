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

from typing import Any, Dict

from django.db.models import Q, QuerySet
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import SmartBuildRecord
from .serializers import SmartBuildRecordFilterInputSLZ


class SmartBuildRecordFilterBackend(BaseFilterBackend):
    """SmartBuild record filter backend"""

    def filter_queryset(
        self,
        request: Request,
        queryset: QuerySet[SmartBuildRecord],
        view: APIView,
    ) -> QuerySet[SmartBuildRecord]:
        slz = SmartBuildRecordFilterInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params: Dict[str, Any] = slz.validated_data

        # 用户只能看到自己操作的数据
        queryset = queryset.filter(operator=request.user)

        if source_origin := params.get("source_origin"):
            queryset = queryset.filter(source_origin=source_origin)

        if search := params.get("search"):
            queryset = queryset.filter(Q(package_name__icontains=search))

        if status := params.get("status"):
            queryset = queryset.filter(status=status)

        if order_by := params.get("order_by"):
            queryset = queryset.order_by(*order_by)

        return queryset
