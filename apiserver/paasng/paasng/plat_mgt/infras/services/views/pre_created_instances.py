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

from paasng.accessories.services.models import Plan, PreCreatedInstance, Service
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.infras.services.serializers import (
    PlanWithPreCreatedInstanceSLZ,
    PreCreatedInstanceOutputSLZ,
    PreCreatedInstanceUpsertSLZ,
)


class PreCreatedInstanceViewSet(viewsets.GenericViewSet):
    """（平台管理）增强服务资源池相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat-mgt.infras.pre_created_instances"],
        operation_description="全量预创建实例列表",
        responses={status.HTTP_200_OK: PlanWithPreCreatedInstanceSLZ(many=True)},
    )
    def list_all_pre_created_instances(self, request, *args, **kwargs):
        qs = Plan.objects.filter(
            service__in=[service for service in Service.objects.all() if service.config.get("provider_name") == "pool"]
        )
        page = self.paginate_queryset(qs)
        return Response(PlanWithPreCreatedInstanceSLZ(page or qs, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.pre_created_instances"],
        operation_description="预创建实例列表",
        responses={status.HTTP_200_OK: PlanWithPreCreatedInstanceSLZ(many=True)},
    )
    def list(self, request, plan_id, *args, **kwargs):
        services = [service for service in Service.objects.all() if service.config.get("provider_name") == "pool"]
        qs = Plan.objects.filter(service__in=services, plan_id=plan_id)
        page = self.paginate_queryset(qs)
        return Response(PlanWithPreCreatedInstanceSLZ(page or qs, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.pre_created_instances"],
        operation_description="创建预创建实例",
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request, plan_id, *args, **kwargs):
        slz = PreCreatedInstanceUpsertSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        plan = Plan.objects.get(uuid=plan_id)
        ins = PreCreatedInstance.objects.create(
            plan=plan,
            config=data["config"],
            credentials=data["credentials"],
            tenant_id=plan.tenant_id,
        )
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ADD_ON,
            attribute=ins.uuid,
            data_after=DataDetail(data=PreCreatedInstanceOutputSLZ(ins).data),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.pre_created_instances"],
        operation_description="更新预创建实例",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, plan_id, instance_id, *args, **kwargs):
        slz = PreCreatedInstanceUpsertSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        instance = PreCreatedInstance.objects.get(plan__uuid=plan_id, uuid=instance_id)
        data_before = PreCreatedInstanceOutputSLZ(instance).data

        instance.config = data["config"]
        instance.credentials = data["credentials"]
        instance.save(update_fields=["config", "credentials"])

        data_after = PreCreatedInstanceOutputSLZ(instance).data
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ADD_ON,
            attribute=instance.uuid,
            data_before=DataDetail(data=data_before),
            data_after=DataDetail(data=data_after),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.pre_created_instances"],
        operation_description="删除预创建实例",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, plan_id, instance_id, *args, **kwargs):
        instance = PreCreatedInstance.objects.get(plan__uuid=plan_id, uuid=instance_id)
        data_before = PreCreatedInstanceOutputSLZ(instance).data
        instance.delete()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ADD_ON,
            attribute=instance_id,
            data_before=DataDetail(data=data_before),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
