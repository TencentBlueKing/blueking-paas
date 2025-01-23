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

from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bcs.client import BCSClient
from paasng.plat_mgt.infras.clusters.serializers import BCSClusterListOutputSLZ, BCSProjectListOutputSLZ


class BCSResourceViewSet(viewsets.GenericViewSet):
    """BCS 资源相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.infras.bcs-resource"],
        operation_description="获取用户有权限的项目",
        responses={status.HTTP_200_OK: BCSProjectListOutputSLZ(many=True)},
    )
    def list_projects(self, request, *args, **kwargs):
        client = BCSClient(get_tenant(request.user).id, request.user.username)
        projects = client.list_auth_projects()
        return Response(data=BCSProjectListOutputSLZ(projects, many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.bcs-resource"],
        operation_description="获取项目下的集群",
        responses={status.HTTP_200_OK: BCSClusterListOutputSLZ(many=True)},
    )
    def list_clusters(self, request, project_id, *args, **kwargs):
        client = BCSClient(get_tenant(request.user).id, request.user.username)
        clusters = client.list_project_clusters(project_id)
        return Response(data=BCSClusterListOutputSLZ(clusters, many=True).data)
