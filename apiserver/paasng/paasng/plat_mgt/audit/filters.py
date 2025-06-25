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

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from rest_framework.filters import BaseFilterBackend

from paasng.misc.audit.models import AdminOperationRecord

from .serializers import OperationAuditFilterInputSLZ


class OperationAuditFilterBackend(BaseFilterBackend):
    """Operation audit filter backend"""

    def filter_queryset(self, request, queryset, view):
        if queryset.model != AdminOperationRecord:
            raise ValueError("OperationAuditFilterBackend only support to filter AdminOperationRecord")

        slz = OperationAuditFilterInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        validate_params = slz.data

        # 操作对象过滤
        target = validate_params.get("target")
        if target is not None:
            queryset = queryset.filter(target=target)

        # 操作类型过滤
        operation = validate_params.get("operation")
        if operation is not None:
            queryset = queryset.filter(operation=operation)

        # 状态过滤
        status = validate_params.get("status")
        if status is not None:
            queryset = queryset.filter(result_code=status)

        # 操作人过滤
        operator = validate_params.get("operator")
        if operator is not None:
            # 将用户名转换成用户对象 ID
            operator = user_id_encoder.encode(settings.USER_TYPE, operator)
            queryset = queryset.filter(user=operator)

        # 时间过滤
        start_time = validate_params.get("start_time")
        end_time = validate_params.get("end_time")
        if start_time is not None:
            queryset = queryset.filter(created__gte=start_time)
        if end_time is not None:
            queryset = queryset.filter(created__lte=end_time)

        return queryset
