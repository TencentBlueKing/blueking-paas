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
from rest_framework import serializers, status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit import constants
from paasng.misc.audit.models import AdminOperationRecord

from .filters import OperationAuditFilterBackend
from .serializers import (
    ApplicationOperationAuditOutputSLZ,
    ApplicationOperationAuditRetrieveOutputSLZ,
    PlatformOperationAuditOutputSLZ,
    PlatformOperationAuditRetrieveOutputSLZ,
)


class BaseOperationAuditViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [OperationAuditFilterBackend]
    pagination_class = LimitOffsetPagination

    list_serializer_class: type[serializers.Serializer] | None = None
    retrieve_serializer_class: type[serializers.Serializer] | None = None

    def list(self, request, *args, **kwargs):
        assert self.list_serializer_class is not None
        queryset = self.get_queryset()
        filter_queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(filter_queryset)
        slz = self.list_serializer_class(page, many=True)
        return self.get_paginated_response(slz.data)

    def retrieve(self, request, uuid, *args, **kwargs):
        assert self.retrieve_serializer_class is not None
        record = get_object_or_404(self.get_queryset(), uuid=uuid)
        slz = self.retrieve_serializer_class(record)
        return Response(slz.data, status=status.HTTP_200_OK)


class ApplicationOperateAuditViewSet(BaseOperationAuditViewSet):
    """应用操作审计"""

    queryset = AdminOperationRecord.objects.exclude(app_code=None).order_by("-created")
    list_serializer_class = ApplicationOperationAuditOutputSLZ
    retrieve_serializer_class = ApplicationOperationAuditRetrieveOutputSLZ


class PlatformOperationAuditViewSet(BaseOperationAuditViewSet):
    """平台操作审计"""

    queryset = AdminOperationRecord.objects.filter(app_code=None).order_by("-created")
    list_serializer_class = PlatformOperationAuditOutputSLZ
    retrieve_serializer_class = PlatformOperationAuditRetrieveOutputSLZ


class AuditEnumsViewSet(viewsets.ViewSet):
    """用来显示过滤审计数据的各种枚举"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list_enum(self, request):
        enum_type = request.query_params.get("type")
        enum_map = {
            "target": constants.OperationTarget,
            "operation": constants.OperationEnum,
            "status": constants.ResultCode,
        }
        enum_cls = enum_map.get(enum_type)
        if not enum_cls or not hasattr(enum_cls, "get_choices"):
            return Response({"detail": "Invalid enum type"}, status=400)
        data = [{"value": value, "label": label} for value, label in enum_cls.get_choices()]
        return Response(data)
