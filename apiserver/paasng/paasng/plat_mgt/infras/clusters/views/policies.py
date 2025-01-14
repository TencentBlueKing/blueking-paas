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

from paas_wl.infras.cluster.models import ClusterAllocationPolicy
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterAllocationPolicyCreateInputSLZ,
    ClusterAllocationPolicyCreateOutputSLZ,
    ClusterAllocationPolicyListOutputSLZ,
    ClusterAllocationPolicyUpdateInputSLZ,
)


class ClusterAllocationPolicyViewSet(viewsets.GenericViewSet):
    """集群分配策略"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    lookup_field = "uuid"
    lookup_url_kwarg = "policy_id"

    def get_queryset(self):
        """获取集群分配策略列表"""
        # FIXME: (多租户)根据平台/租户管理员身份，返回不同的集群分配策略列表
        return ClusterAllocationPolicy.objects.all()

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_allocation_policy"],
        operation_description="获取集群分配策略",
        responses={status.HTTP_200_OK: ClusterAllocationPolicyListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取集群分配策略"""
        policies = self.get_queryset()
        return Response(data=ClusterAllocationPolicyListOutputSLZ(policies, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_allocation_policy"],
        operation_description="新建集群分配策略",
        request_body=ClusterAllocationPolicyCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: ClusterAllocationPolicyCreateOutputSLZ()},
    )
    def create(self, request, *args, **kwargs):
        """新建集群分配策略"""
        slz = ClusterAllocationPolicyCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        policy = ClusterAllocationPolicy.objects.create(**data)
        return Response(
            status=status.HTTP_201_CREATED,
            data=ClusterAllocationPolicyCreateOutputSLZ(policy).data,
        )

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_allocation_policy"],
        operation_description="更新集群分配策略",
        request_body=ClusterAllocationPolicyUpdateInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, *args, **kwargs):
        """更新集群分配策略"""
        policy = self.get_object()

        slz = ClusterAllocationPolicyUpdateInputSLZ(
            data=request.data,
            context={"cur_tenant_id": policy.tenant_id},
        )
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        policy.type = data["type"]
        policy.allocation_policy = data["allocation_policy"]
        policy.allocation_precedence_policies = data["allocation_precedence_policies"]
        policy.save(update_fields=["type", "allocation_policy", "allocation_precedence_policies", "updated"])

        return Response(status=status.HTTP_204_NO_CONTENT)
