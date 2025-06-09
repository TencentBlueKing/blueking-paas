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

from rest_framework import viewsets
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


class ApplicationOperateAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """应用操作审计"""

    queryset = AdminOperationRecord.objects.exclude(app_code=None).order_by("-created")
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [OperationAuditFilterBackend]
    pagination_class = LimitOffsetPagination
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationOperationAuditOutputSLZ
        return ApplicationOperationAuditRetrieveOutputSLZ


class PlatformOperationAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """平台操作审计"""

    queryset = AdminOperationRecord.objects.filter(app_code=None).order_by("-created")
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    filter_backends = [OperationAuditFilterBackend]
    pagination_class = LimitOffsetPagination
    lookup_field = "uuid"
    list_serializer_class = PlatformOperationAuditOutputSLZ
    retrieve_serializer_class = PlatformOperationAuditRetrieveOutputSLZ

    def get_serializer_class(self):
        if self.action == "list":
            return PlatformOperationAuditOutputSLZ
        return PlatformOperationAuditRetrieveOutputSLZ


class AuditFilterOptionsViewSet(viewsets.ViewSet):
    """用来显示过滤审计数据的各种枚举"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request):
        """列出所有可用过滤的枚举类型"""
        enum_map = {
            "target": constants.OperationTarget,
            "operation": constants.OperationEnum,
            "status": constants.ResultCode,
        }
        data = {}
        for key, enum_cls in enum_map.items():
            if hasattr(enum_cls, "get_choices"):
                data[key] = [{"value": value, "label": label} for value, label in enum_cls.get_choices()]
            else:
                data[key] = []
        return Response(data)
