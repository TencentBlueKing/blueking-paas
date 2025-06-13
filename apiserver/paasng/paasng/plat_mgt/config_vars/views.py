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
from paasng.platform.engine.models.config_var import BuiltinConfigVar

from .serializers import (
    BuiltinConfigVarCreateInputSLZ,
    BuiltinConfigVarOutputSLZ,
    BuiltinConfigVarUpdateInputSLZ,
)


class BuiltinConfigVarViewSet(viewsets.GenericViewSet):
    """内建环境变量管理"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.builtin_config_vars"],
        operation_description="获取内建环境变量列表",
        responses={status.HTTP_200_OK: BuiltinConfigVarOutputSLZ(many=True)},
    )
    def list(self, request):
        """列出所有内建环境变量"""
        config_vars = BuiltinConfigVar.objects.order_by("-created")
        return Response(BuiltinConfigVarOutputSLZ(config_vars, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.builtin_config_vars"],
        operation_description="创建内建环境变量",
        responses={status.HTTP_201_CREATED: BuiltinConfigVarOutputSLZ()},
    )
    def create(self, request):
        """创建内建环境变量"""
        slz = BuiltinConfigVarCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        BuiltinConfigVar.objects.create(
            key=data["key"],
            value=data["value"],
            description=data["description"],
            operator=request.user,
        )

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ENV_VAR,
            attribute=data["key"],
            data_after=DataDetail(
                data={"key": data["key"], "value": data["value"], "description": data["description"]},
            ),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.builtin_config_vars"],
        operation_description="更新内建环境变量",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, pk):
        """更新内建环境变量"""
        slz = BuiltinConfigVarUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        config_var = get_object_or_404(BuiltinConfigVar, pk=pk)
        data_before = DataDetail(
            data={"key": config_var.key, "value": config_var.value, "description": config_var.description},
        )

        config_var.value = data["value"]
        config_var.description = data["description"]
        config_var.operator = request.user
        config_var.save(update_fields=["value", "description", "operator", "updated"])

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            attribute=config_var.key,
            data_before=data_before,
            data_after=DataDetail(
                data={"key": config_var.key, "value": data["value"], "description": data["description"]},
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.builtin_config_vars"],
        operation_description="删除内建环境变量",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, pk):
        """删除内建环境变量"""
        config_var = get_object_or_404(BuiltinConfigVar, pk=pk)
        config_var.delete()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ENV_VAR,
            attribute=config_var.key,
            data_before=DataDetail(
                data={"key": config_var.key, "value": config_var.value, "description": config_var.description},
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
