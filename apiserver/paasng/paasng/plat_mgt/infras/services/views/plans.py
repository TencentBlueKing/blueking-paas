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

from typing import Tuple

from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub.manager import mixed_plan_mgr, mixed_service_mgr
from paasng.accessories.servicehub.remote.exceptions import UnsupportedOperationError
from paasng.accessories.servicehub.services import NOTSET, PlanObj, ServiceObj
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.infras.services.serializers import (
    BasePlanObjSLZ,
    PlanUpsertInputSLZ,
    PlanWithSvcSLZ,
)
from paasng.utils.error_codes import error_codes


class PlanViewSet(viewsets.GenericViewSet):
    """（平台管理员）增强服务方案管理，接入相关 API"""

    # TODO: 支持租户管理权限校验后，不能再全量返回所有策略，而是根据租户ID进行过滤
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def get_service_and_plan(self, service_id, plan_id, tenant_id) -> Tuple[ServiceObj, PlanObj]:
        """需要返回 service 和 plan 两个对象，不然 service 被垃圾回收后，plan 无法获取到 service 对象"""
        service = mixed_service_mgr.get(uuid=service_id)
        plans = service.get_plans_by_tenant_id(is_active=NOTSET, tenant_id=tenant_id)
        plan = next((plan for plan in plans if plan.uuid == plan_id), None)
        if not plan:
            raise Http404("PlanObjNotFound")
        return service, plan

    @swagger_auto_schema(
        tags=["plat-mgt.infras.plans"],
        operation_description="全量增强服务方案列表",
        responses={status.HTTP_200_OK: PlanWithSvcSLZ(many=True)},
    )
    def list_all(self, request, *args, **kwargs):
        """获取所有服务的方案列表"""
        plans = mixed_plan_mgr.list()
        return Response(data=PlanWithSvcSLZ(plans, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.plans"],
        operation_description="租户下增强服务方案列表",
        responses={status.HTTP_200_OK: PlanWithSvcSLZ(many=True)},
    )
    def list(self, request, service_id, tenant_id, *args, **kwargs):
        service = mixed_service_mgr.get(uuid=service_id)
        plans = service.get_plans_by_tenant_id(is_active=NOTSET, tenant_id=tenant_id)
        return Response(data=PlanWithSvcSLZ(plans, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.plans"],
        operation_description="增强服务方案",
        responses={status.HTTP_200_OK: PlanWithSvcSLZ()},
    )
    def retrieve(self, request, service_id, tenant_id, plan_id, *args, **kwargs):
        service, plan = self.get_service_and_plan(service_id, plan_id, tenant_id)
        return Response(data=PlanWithSvcSLZ(plan).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.plans"],
        operation_description="创建增强服务方案",
        request_body=PlanUpsertInputSLZ(),
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request, service_id, tenant_id, *args, **kwargs):
        slz = PlanUpsertInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        data["tenant_id"] = tenant_id

        service = mixed_service_mgr.get(uuid=service_id)
        try:
            mixed_plan_mgr.create(service, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name} - {data['name']}",
            data_after=DataDetail(data=data),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.plans"],
        operation_description="删除增强服务方案",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, service_id, tenant_id, plan_id, *args, **kwargs):
        service, plan = self.get_service_and_plan(service_id, plan_id, tenant_id)
        data_before = DataDetail(data=BasePlanObjSLZ(plan).data)

        try:
            mixed_plan_mgr.delete(service, plan_id)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name}" + (f" - {plan.name}" if plan else ""),
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.plans"],
        operation_description="更新增强服务方案",
        request_body=PlanUpsertInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, service_id, tenant_id, plan_id, *args, **kwargs):
        slz = PlanUpsertInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        data["tenant_id"] = tenant_id

        service, plan = self.get_service_and_plan(service_id, plan_id, tenant_id)
        data_before = DataDetail(data=BasePlanObjSLZ(plan).data)

        try:
            mixed_plan_mgr.update(service, plan_id=plan_id, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        service, plan = self.get_service_and_plan(service_id, plan_id, tenant_id)
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name}" + (f" - {plan.name}" if plan else ""),
            data_before=data_before,
            data_after=DataDetail(data=BasePlanObjSLZ(plan).data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# TODO: plan pre_created_instances 相关的接口从 admin42 迁移到这边来
