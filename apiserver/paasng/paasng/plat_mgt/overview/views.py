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

import logging
from typing import List

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.models import ClusterAllocationPolicy
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import ServiceBindingPolicy, ServiceBindingPrecedencePolicy
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bk_user.client import BkUserClient
from paasng.infras.bk_user.entities import Tenant
from paasng.plat_mgt.overview.serializers import TenantConfigStatusOutputSLZ

logger = logging.getLogger(__name__)


class PlatMgtOverviewViewSet(viewsets.GenericViewSet):
    """平台管理概览相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.overview"],
        operation_description="获取租户配置情况",
        responses={status.HTTP_200_OK: TenantConfigStatusOutputSLZ(many=True)},
    )
    def list_tenant_config_statuses(self, request, *args, **kwargs):
        tenants = self._get_tenants()
        addons_services = mixed_service_mgr.list()
        tenant_ids = [tenant.id for tenant in tenants]

        # 集群分配策略
        cluster_allocation_policy_tenant_ids = set(
            ClusterAllocationPolicy.objects.filter(tenant_id__in=tenant_ids).values_list("tenant_id", flat=True)
        )
        # 增强服务绑定策略
        service_binding_policy_tenant_service_ids = {
            (p.tenant_id, str(p.service_id)) for p in ServiceBindingPolicy.objects.filter(tenant_id__in=tenant_ids)
        }
        # 增强服务绑定策略（带优先级）
        service_binding_precedence_policy_tenant_service_ids = {
            (p.tenant_id, str(p.service_id))
            for p in ServiceBindingPrecedencePolicy.objects.filter(tenant_id__in=tenant_ids)
        }

        resp_data = [
            {
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "cluster": {
                    "allocated": tenant.id in cluster_allocation_policy_tenant_ids,
                },
                "addons_services": [
                    {
                        "id": svc.uuid,
                        "name": svc.name,
                        "bind": (tenant.id, svc.uuid) in service_binding_policy_tenant_service_ids
                        or (tenant.id, svc.uuid) in service_binding_precedence_policy_tenant_service_ids,
                    }
                    for svc in addons_services
                ],
            }
            for tenant in tenants
        ]

        return Response(data=TenantConfigStatusOutputSLZ(resp_data, many=True).data)

    def _get_tenants(self) -> List[Tenant]:
        # FIXME: (多租户) 根据平台/租户管理员身份，返回不同的租户列表
        user_tenant_id = get_tenant(self.request.user).id
        return BkUserClient(user_tenant_id).list_tenants()
