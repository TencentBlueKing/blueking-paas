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

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.local.manager import LocalServiceMgr
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.remote.exceptions import UnsupportedOperationError
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.infras.services.serializers import (
    ServiceCreateSLZ,
    ServiceObjOutputListSLZ,
    ServiceObjOutputSLZ,
    ServiceUpdateSLZ,
)
from paasng.utils.error_codes import error_codes


class ServiceViewSet(viewsets.GenericViewSet):
    """（平台管理）增强服务相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="增强服务列表",
        responses={status.HTTP_200_OK: ServiceObjOutputListSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        services = mixed_service_mgr.list()
        return Response(data=ServiceObjOutputListSLZ(services, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="创建增强服务",
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request, *args, **kwargs):
        slz = ServiceCreateSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        # 只支持创建本地增强服务
        LocalServiceMgr().create(data)
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ADD_ON,
            attribute=data["name"],
            data_after=DataDetail(data=data),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="更新增强服务",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, service_id, *args, **kwargs):
        try:
            service = mixed_service_mgr.get(uuid=service_id)
        except ServiceObjNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)

        slz = ServiceUpdateSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        data_before = ServiceObjOutputSLZ(service).data
        # logo 字段太长，前端比较时会导致浏览器 OOM
        del data_before["logo"]

        try:
            mixed_service_mgr.update(service, data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        service = mixed_service_mgr.get(uuid=service_id)
        data_after = ServiceObjOutputSLZ(service).data
        del data_after["logo"]
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ADD_ON,
            attribute=service.name,
            data_before=DataDetail(data=data_before),
            data_after=DataDetail(data=data_after),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="删除增强服务",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, service_id, *args, **kwargs):
        service = mixed_service_mgr.get(uuid=service_id)
        data_before = DataDetail(data=ServiceObjOutputSLZ(service).data)

        try:
            mixed_service_mgr.destroy(service)
        except UnsupportedOperationError as e:
            raise error_codes.UNSUPPORTED_OPERATION.f(str(e))

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ADD_ON,
            attribute=service.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
