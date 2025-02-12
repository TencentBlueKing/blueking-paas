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

from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub.manager import mixed_plan_mgr, mixed_service_mgr
from paasng.accessories.servicehub.remote.exceptions import UnsupportedOperationError
from paasng.accessories.servicehub.services import NOTSET, PlanObj
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_mgt.infras.services.serializers import (
    PlanCreateInputSLZ,
    PlanOutputSLZ,
    PlanUpdateInputSLZ,
)
from paasng.utils.error_codes import error_codes


class PlanViewSet(viewsets.GenericViewSet):
    """（租户管理员）增强服务方案管理，接入相关 API"""

    # TODO：校验租户管理员权限
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def get_plan(self, service_id, plan_id) -> PlanObj:
        service = mixed_service_mgr.get(uuid=service_id)
        plans = service.get_plans(is_active=NOTSET)
        plan = next((plan for plan in plans if plan.uuid == plan_id), None)
        if not plan:
            raise Http404("ServiceObjNotFound")
        return plan

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="全量增强服务方案列表",
        responses={status.HTTP_200_OK: PlanOutputSLZ(many=True)},
    )
    def list_all(self, request, *args, **kwargs):
        """获取所有服务的方案列表"""
        tenant_id = get_tenant(request.user).id
        plans = mixed_plan_mgr.list_by_tenant_id(tenant_id)
        return Response(data=PlanOutputSLZ(plans, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="增强服务方案列表",
        responses={status.HTTP_200_OK: PlanOutputSLZ(many=True)},
    )
    def list(self, request, service_id, *args, **kwargs):
        service = mixed_service_mgr.get(uuid=service_id)
        plans = service.get_plans(is_active=NOTSET)
        return Response(data=PlanOutputSLZ(plans, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="增强服务方案",
        responses={status.HTTP_200_OK: PlanOutputSLZ()},
    )
    def retrieve(self, request, service_id, plan_id, *args, **kwargs):
        plan = self.get_plan(service_id, plan_id)
        return Response(data=PlanOutputSLZ(plan).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="创建增强服务方案",
        request_body=PlanCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request, service_id, *args, **kwargs):
        slz = PlanCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service = mixed_service_mgr.get(uuid=service_id)
        try:
            mixed_plan_mgr.create(service, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name} - {data['name']}",
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="删除增强服务方案",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, service_id, plan_id, *args, **kwargs):
        service = mixed_service_mgr.get(uuid=service_id)
        plan = self.get_plan(service_id, plan_id)
        data_before = DataDetail(type=DataType.RAW_DATA, data=PlanOutputSLZ(plan).data)

        try:
            mixed_plan_mgr.delete(service, plan_id)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name}" + (f" - {plan.name}" if plan else ""),
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.services"],
        operation_description="更新增强服务方案",
        request_body=PlanUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, service_id, plan_id, *args, **kwargs):
        slz = PlanUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service = mixed_service_mgr.get(uuid=service_id)

        plan = self.get_plan(service_id, plan_id)
        data_before = DataDetail(type=DataType.RAW_DATA, data=PlanOutputSLZ(plan).data)

        try:
            mixed_plan_mgr.update(service, plan_id=plan_id, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        plan = self.get_plan(service_id, plan_id)
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name}" + (f" - {plan.name}" if plan else ""),
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=PlanOutputSLZ(plan).data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# TODO: plan pre_created_instances 相关的接口从 admin42 迁移到这边来
