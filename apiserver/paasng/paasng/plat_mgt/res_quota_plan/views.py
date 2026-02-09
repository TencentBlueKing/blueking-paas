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
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.platform.bkapp_model.constants import CPUResourceQuantity, MemoryResourceQuantity
from paasng.platform.bkapp_model.models import ResQuotaPlan
from paasng.utils.error_codes import error_codes

from .serializers import ResQuotaPlanInputSLZ, ResQuotaPlanOutputSLZ


class ResourceQuotaPlanViewSet(viewsets.GenericViewSet):
    """资源配额方案管理"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.res_quota_plans"],
        operation_description="列出所有资源配额方案",
        responses={status.HTTP_200_OK: ResQuotaPlanOutputSLZ(many=True)},
    )
    def list(self, request):
        """列出所有资源配额方案"""

        queryset = ResQuotaPlan.objects.all().order_by("created")
        serializer = ResQuotaPlanOutputSLZ(queryset, many=True)

        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["plat_mgt.res_quota_plans"],
        operation_description="创建资源配额方案",
        request_body=ResQuotaPlanInputSLZ,
        responses={status.HTTP_201_CREATED: None},
    )
    def create(self, request):
        """创建资源配额方案"""
        slz = ResQuotaPlanInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        ResQuotaPlan.objects.create(**data)

        add_plat_mgt_audit_record(
            user=request.user,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PROCESS_SPEC_PLAN,
            data_after=DataDetail(data=data),
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.res_quota_plans"],
        operation_description="更新资源配额方案",
        request_body=ResQuotaPlanInputSLZ,
        responses={status.HTTP_200_OK: None},
    )
    def update(self, request, pk):
        """更新资源配额方案"""

        plan_obj = get_object_or_404(ResQuotaPlan, pk=pk)

        if plan_obj.is_builtin:
            return Response({"detail": _("系统内置方案不允许修改")}, status=status.HTTP_403_FORBIDDEN)

        slz = ResQuotaPlanInputSLZ(data=request.data, instance=plan_obj)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        data_before = ResQuotaPlanInputSLZ(plan_obj).data

        plan_obj.name = data["name"]
        plan_obj.limits = data["limits"]
        plan_obj.requests = data["requests"]
        plan_obj.is_active = data.get("is_active", plan_obj.is_active)
        plan_obj.save()

        data_after = ResQuotaPlanInputSLZ(plan_obj).data

        add_plat_mgt_audit_record(
            user=request.user,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PROCESS_SPEC_PLAN,
            data_before=DataDetail(data=data_before),
            data_after=DataDetail(data=data_after),
        )

        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat_mgt.res_quota_plans"],
        operation_description="删除资源配额方案",
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def destroy(self, request, pk):
        """删除资源配额方案"""

        plan_obj = get_object_or_404(ResQuotaPlan, pk=pk)
        if plan_obj.is_builtin:
            raise PermissionDenied(_("系统内置方案不允许删除"))

        if used_by_processes := plan_obj.get_used_by_processes():
            raise error_codes.CANNOT_DELETE_RES_QUOTA_PLAN.f(_("该方案已被应用进程引用")).set_data(
                {"used_by_processes": used_by_processes}
            )

        data_before = ResQuotaPlanOutputSLZ(plan_obj).data
        plan_obj.delete()

        add_plat_mgt_audit_record(
            user=request.user,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PROCESS_SPEC_PLAN,
            data_before=DataDetail(data=data_before),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.res_quota_plans"],
        operation_description="获取自定义资源配置的可选项列表 (CPU 和内存的预设值)",
        responses={status.HTTP_200_OK: None},
    )
    def list_quantity_options(self, request):
        """获取自定义资源配置的可选项列表 (CPU 和内存的预设值)"""

        cpu_resource_quantity = [
            {"value": value, "label": label} for value, label in CPUResourceQuantity.get_choices()
        ]
        memory_resource_quantity = [
            {"value": value, "label": label} for value, label in MemoryResourceQuantity.get_choices()
        ]

        result = {
            "cpu_resource_quantity": cpu_resource_quantity,
            "memory_resource_quantity": memory_resource_quantity,
        }

        return Response(result, status=status.HTTP_200_OK)
