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

from paasng.accessories.servicehub.binding_policy.manager import ServiceBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.core.tenant.user import OP_TYPE_TENANT_ID, get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.services.serializers import (
    DeletePolicyCombinationSLZ,
    PolicyCombinationConfigSLZ,
)
from paasng.utils.error_codes import error_codes


class BindingPolicyViewSet(viewsets.GenericViewSet):
    """增强服务绑定策略管理"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def check_tenant_permission(self, request, tenant_id: str):
        """校验 tenant_id 权限, 除运营租户外, 仅支持操作当前租户的资源"""
        # TODO: 使用统一的方式校验 tenant 权限
        user_tenant_id = get_tenant(request.user).id
        if user_tenant_id not in [OP_TYPE_TENANT_ID, tenant_id]:
            raise error_codes.TENANT_PERMISSION_DENIED

    @swagger_auto_schema(
        tags=["plat-mgt.infras.binding_policies"],
        operation_description="增强服务方案绑定策略列表",
        responses={status.HTTP_200_OK: PolicyCombinationConfigSLZ(many=True)},
    )
    def list(self, request, service_id, *args, **kwargs):
        tenant_id = get_tenant(request.user).id
        service = mixed_service_mgr.get(uuid=service_id)
        mgr = ServiceBindingPolicyManager(service, tenant_id)
        configs = mgr.get_policy_combination_configs()
        # TODO: 运营租户暂时只获取了已存在的 Plan，没有返回未配置 Plan 的租户信息
        return Response(data=PolicyCombinationConfigSLZ(configs, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.binding_policies"],
        operation_description="创建/更新增强服务方案绑定策略",
        request_body=PolicyCombinationConfigSLZ(),
        responses={status.HTTP_200_OK: PolicyCombinationConfigSLZ(many=True)},
    )
    def upsert(self, request, service_id, *args, **kwargs):
        slz = PolicyCombinationConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        self.check_tenant_permission(request, data.tenant_id)

        service = mixed_service_mgr.get(uuid=service_id)
        mgr = ServiceBindingPolicyManager(service, data.tenant_id)
        mgr.upsert_policy_combination(data)
        return Response(status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.binding_policies"],
        operation_description="删除增强服务方案绑定策略",
        query_serializer=DeletePolicyCombinationSLZ,
        responses={status.HTTP_200_OK: PolicyCombinationConfigSLZ(many=True)},
    )
    def destroy(self, request, service_id, *args, **kwargs):
        slz = DeletePolicyCombinationSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        self.check_tenant_permission(request, data.get("tenant_id"))

        service = mixed_service_mgr.get(uuid=service_id)
        mgr = ServiceBindingPolicyManager(service, data.get("tenant_id"))
        mgr.clean_policy_combination()
        return Response(status=status.HTTP_204_NO_CONTENT)
