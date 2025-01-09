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

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.bcs.client import BCSClient
from paasng.plat_mgt.infras.clusters.serializers import BCSClusterListOutputSLZ, BCSProjectListOutputSLZ


class BCSResourceViewSet(viewsets.GenericViewSet):
    """BCS 资源相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list_projects(self, request, *args, **kwargs):
        projects = BCSClient(request.user.username).list_projects()
        return Response(data=BCSProjectListOutputSLZ(projects, many=True).data)

    def list_clusters(self, request, project_id, *args, **kwargs):
        clusters = BCSClient(request.user.username).list_clusters(project_id)
        return Response(data=BCSClusterListOutputSLZ(clusters, many=True).data)
