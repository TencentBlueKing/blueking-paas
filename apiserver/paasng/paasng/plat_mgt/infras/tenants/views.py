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

from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.infras.cluster.models import Cluster
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.tenants.serializers import AvailableClusterListOutputSLZ


class TenantAvailableClusterViewSet(viewsets.GenericViewSet):
    """租户可用集群 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster"],
        operation_description="获取本租户可用集群",
        responses={status.HTTP_200_OK: AvailableClusterListOutputSLZ(many=True)},
    )
    def list(self, request, tenant_id, *args, **kwargs):
        # 本租户的集群本租户一定是可用的，其他租户的集群，如果有对应的配置，则可用
        clusters = Cluster.objects.filter(Q(tenant_id=tenant_id) | Q(available_tenant_ids__contains=tenant_id))
        return Response(data=AvailableClusterListOutputSLZ(clusters, many=True).data)
