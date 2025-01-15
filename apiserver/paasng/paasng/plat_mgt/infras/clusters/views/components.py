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

from paas_wl.infras.cluster.models import ClusterComponent
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.clusters.constants import ClusterComponentStatus
from paasng.plat_mgt.infras.clusters.helm import HelmClient
from paasng.plat_mgt.infras.clusters.k8s import K8SWorkloadStateGetter
from paasng.plat_mgt.infras.clusters.serializers import (
    ClusterComponentListOutputSLZ,
    ClusterComponentRetrieveOutputSLZ,
    ClusterComponentUpsertInputSLZ,
)
from paasng.plat_mgt.infras.clusters.values.getters import get_values_getter_cls


class ClusterComponentViewSet(viewsets.GenericViewSet):
    """集群组件管理"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def get_queryset(self):
        # FIXME：（多租户）根据平台/租户管理员身份，返回不同的集群组件列表
        # 必要组件排前面，然后按照字母序排序
        return ClusterComponent.objects.filter(
            cluster__name=self.kwargs["cluster_name"],
        ).order_by("-required", "name")

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_components"],
        operation_description="获取集群组件列表",
        responses={status.HTTP_200_OK: ClusterComponentListOutputSLZ(many=True)},
    )
    def list(self, request, cluster_name, *args, **kwargs):
        release_map = {r.name: r for r in HelmClient(cluster_name).list_releases()}

        components = []
        for comp in self.get_queryset():
            # 从 helm release 中获取组件部署状态
            status = ClusterComponentStatus.NOT_INSTALLED
            if rel := release_map.get(comp.name):
                status = ClusterComponentStatus.from_helm_release_status(rel.deploy_result.status)

            components.append({"name": comp.name, "required": comp.required, "status": status})

        return Response(data=ClusterComponentListOutputSLZ(components, many=True).data)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_components"],
        operation_description="更新或新建集群组件",
        request_body=ClusterComponentUpsertInputSLZ,
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def upsert(self, request, cluster_name, component_name, *args, **kwargs):
        # FIXME 需要注意：
        # 1. 需要检查组件是否已经在集群中已存在
        # 2. 如果组件已经部署，需要制定成对应的命名空间镜像更新
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat-mgt.infras.cluster_components"],
        operation_description="获取集群组件详情",
        responses={status.HTTP_200_OK: ClusterComponentRetrieveOutputSLZ()},
    )
    def retrieve(self, request, cluster_name, component_name, *args, **kwargs):
        release = HelmClient(cluster_name).get_release(component_name)
        if not release:
            return Response(status=status.HTTP_404_NOT_FOUND)

        workload_states = K8SWorkloadStateGetter(cluster_name, release).get_states()
        values_getter = get_values_getter_cls(component_name)(release)

        component = {
            "chart": release.chart,
            "release": {
                "name": release.name,
                "namespace": release.namespace,
                "created_at": release.deploy_result.created_at,
                "description": release.deploy_result.description,
                "status": release.deploy_result.status,
            },
            "values": values_getter.get(),
            "workloads": workload_states,
        }
        return Response(data=ClusterComponentRetrieveOutputSLZ(component).data)
