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
from paasng.platform.bkapp_model.models import ProcessComponent

from .serializers import (
    ProcessComponentCreateInputSLZ,
    ProcessComponentOutputSLZ,
    ProcessComponentUpdateInputSLZ,
)


class ProcessComponentViewSet(viewsets.GenericViewSet):
    """
    TODO: 在操作 ApiServer ProcessComponent 时，可以直接操作集群内的进程组件模版
    进程组件管理
    """

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.proc_components"],
        operation_description="获取进程组件列表",
        responses={status.HTTP_200_OK: ProcessComponentOutputSLZ(many=True)},
    )
    def list(self, request):
        """列出所有进程组件"""
        proc_components = ProcessComponent.objects.order_by("-created")
        return Response(ProcessComponentOutputSLZ(proc_components, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.proc_components"],
        operation_description="创建进程组件",
        responses={status.HTTP_201_CREATED: ProcessComponentCreateInputSLZ()},
    )
    def create(self, request):
        """创建进程组件"""
        slz = ProcessComponentCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        component = ProcessComponent.objects.create(
            type=data["type"],
            version=data["version"],
            enabled=data["enabled"],
            description=data["description"],
            docs_url=data["docs_url"],
            property_json_schema=data["property_json_schema"],
        )

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PROC_COMPONENT,
            attribute=f"{component.type}:{component.version}",
            data_after=DataDetail(
                data=ProcessComponentOutputSLZ(component).data,
            ),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.proc_components"],
        operation_description="更新进程组件",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, pk):
        """更新进程组件"""
        slz = ProcessComponentUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        component = get_object_or_404(ProcessComponent, pk=pk)
        data_before = DataDetail(
            data=ProcessComponentOutputSLZ(component).data,
        )

        component.enabled = data["enabled"]
        component.description = data["description"]
        component.docs_url = data["docs_url"]
        component.property_json_schema = data["property_json_schema"]
        component.save(update_fields=["enabled", "description", "docs_url", "property_json_schema"])

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PROC_COMPONENT,
            attribute=f"{component.type}:{component.version}",
            data_before=data_before,
            data_after=DataDetail(
                data=ProcessComponentOutputSLZ(component).data,
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.proc_components"],
        operation_description="删除进程组件",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, uuid):
        """删除进程组件"""
        component = get_object_or_404(ProcessComponent, uuid=uuid)
        component.delete()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PROC_COMPONENT,
            attribute=f"{component.type}:{component.version}",
            data_before=DataDetail(
                data=ProcessComponentOutputSLZ(component).data,
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
