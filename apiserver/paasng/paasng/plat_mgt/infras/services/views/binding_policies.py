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

from paasng.accessories.servicehub.binding_policy.manager import (
    SvcBindingPolicyManager,
    list_policy_combination_configs,
)
from paasng.accessories.servicehub.constants import PrecedencePolicyCondType
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.services.models import ServiceCategory
from paasng.accessories.services.providers import get_active_provider_choices
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.services.serializers import (
    DeletePolicyCombinationSLZ,
    PolicyCombinationConfigOutputSLZ,
    PolicyCombinationConfigUpsertSLZ,
    PrecedencePolicyCondTypeOutputSLZ,
)


class BindingPolicyViewSet(viewsets.GenericViewSet):
    """（平台管理员）增强服务绑定策略管理"""

    # TODO: 支持租户管理权限校验后，不能再全量返回所有策略，而是根据租户ID进行过滤
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat-mgt.infras.binding_policies"],
        operation_description="增强服务方案绑定策略列表",
        responses={status.HTTP_200_OK: PolicyCombinationConfigOutputSLZ(many=True)},
    )
    def list(self, request, service_id, *args, **kwargs):
        service = mixed_service_mgr.get(uuid=service_id)
        configs = list_policy_combination_configs(service)
        return Response(data=PolicyCombinationConfigOutputSLZ(configs, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.binding_policies"],
        operation_description="创建/更新增强服务方案绑定策略",
        request_body=PolicyCombinationConfigUpsertSLZ(),
        responses={status.HTTP_200_OK: PolicyCombinationConfigOutputSLZ(many=True)},
    )
    def upsert(self, request, service_id, *args, **kwargs):
        slz = PolicyCombinationConfigUpsertSLZ(data=request.data, context={"service_id": service_id})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service = mixed_service_mgr.get(uuid=service_id)
        mgr = SvcBindingPolicyManager(service, getattr(data, "tenant_id"))
        mgr.save_comb_cfg(data)
        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.binding_policies"],
        operation_description="删除增强服务方案绑定策略",
        query_serializer=DeletePolicyCombinationSLZ,
        responses={status.HTTP_200_OK: PolicyCombinationConfigOutputSLZ(many=True)},
    )
    def destroy(self, request, service_id, *args, **kwargs):
        slz = DeletePolicyCombinationSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service = mixed_service_mgr.get(uuid=service_id)
        mgr = SvcBindingPolicyManager(service, data.get("tenant_id"))
        mgr.clean()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.binding_policies"],
        operation_description="获取方案绑定分配策略条件",
        responses={status.HTTP_200_OK: PrecedencePolicyCondTypeOutputSLZ()},
    )
    def list_condition_types(self, request, *args, **kwargs):
        cond_types = [{"key": k, "name": n} for k, n in PrecedencePolicyCondType.get_django_choices()]
        return Response(data=PrecedencePolicyCondTypeOutputSLZ(cond_types, many=True).data)


class CategoryViewSet(viewsets.GenericViewSet):
    """（平台管理员）增强服务类别"""

    # TODO: 支持租户管理权限校验后，不能再全量返回所有策略，而是根据租户ID进行过滤
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat-mgt.infras.category"],
        operation_description="增强服务类别列表",
    )
    def list(self, request, *args, **kwargs):
        category_list = {
            "category_list": [
                {"value": category.id, "text": category.name} for category in ServiceCategory.objects.all()
            ]
        }
        return Response(data=category_list)


class ProviderViewSet(viewsets.GenericViewSet):
    """（平台管理员）增强服务提供商"""

    # TODO: 支持租户管理权限校验后，不能再全量返回所有策略，而是根据租户ID进行过滤
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat-mgt.infras.provider"],
        operation_description="增强服务提供商",
    )
    def list(self, request, *args, **kwargs):
        provider_choices = {"provider_choices": get_active_provider_choices()}
        return Response(data=provider_choices)
