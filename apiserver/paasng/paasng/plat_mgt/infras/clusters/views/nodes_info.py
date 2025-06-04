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

from paas_wl.bk_app.applications.models.app import App
from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterNodesInfoListInputSLZ,
    ClusterNodesInfoListOutputSLZ,
    ClusterNodesSyncInfoOutputSLZ,
)


class ClusterNodesInfoViewSet(viewsets.GenericViewSet):
    """集群节点信息"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def _get_cluster_info(self, cluster_name):
        cluster_state = RegionClusterState.objects.get(cluster_name=cluster_name)
        bindings = RCStateAppBinding.objects.filter(state_id=cluster_state.id)
        app_uuids = bindings.values_list("app__uuid", flat=True)

        return {
            "cluster_state": cluster_state,
            # 去重
            "binding_app_codes": list({app.paas_app_code for app in App.objects.filter(uuid__in=app_uuids)}),
        }

    def _get_nodes_info_data(self, cluster_name):
        cluster_info = self._get_cluster_info(cluster_name)
        nodes = cluster_info["cluster_state"].nodes_name or []
        binding_apps = cluster_info["binding_app_codes"]
        created_at = cluster_info["cluster_state"].created
        return {"nodes": nodes, "binding_apps": binding_apps, "created_at": created_at}

    def _get_sync_record_data(self, cluster_name):
        cluster_info = self._get_cluster_info(cluster_name)
        nodes = cluster_info["cluster_state"].nodes_name or []
        binding_apps = cluster_info["binding_app_codes"]
        nodes_cnt = cluster_info["cluster_state"].nodes_cnt or 0
        created_at = cluster_info["cluster_state"].created
        return {"nodes": nodes, "binding_apps": binding_apps, "nodes_cnt": nodes_cnt, "created_at": created_at}

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_nodes_info"],
        operation_description="集群节点信息",
        request_body=ClusterNodesInfoListInputSLZ,
        responses={status.HTTP_200_OK: ClusterNodesInfoListOutputSLZ()},
    )
    def list_nodes_info(self, request, *args, **kwargs):
        slz = ClusterNodesInfoListInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        info = self._get_nodes_info_data(slz.validated_data["cluster_name"])
        return Response(ClusterNodesInfoListOutputSLZ(info).data)

    @swagger_auto_schema(
        tags=["plat_mgt.infras.cluster_sync_records"],
        operation_description="节点同步记录",
        request_body=ClusterNodesInfoListInputSLZ,
        responses={status.HTTP_200_OK: ClusterNodesSyncInfoOutputSLZ()},
    )
    def list_sync_records(self, request, *args, **kwargs):
        slz = ClusterNodesInfoListInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        info = self._get_sync_record_data(slz.validated_data["cluster_name"])
        return Response(ClusterNodesSyncInfoOutputSLZ(info).data)
