# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from collections import defaultdict
from dataclasses import asdict
from typing import Optional

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet, mixins

from paas_wl.apis.admin.helpers.helm import (
    HelmReleaseParser,
    WorkloadsDetector,
    convert_secrets_to_releases,
    filter_latest_releases,
)
from paas_wl.apis.admin.helpers.operator import detect_operator_status, fetch_paas_cobj_info
from paas_wl.apis.admin.serializers.clusters import (
    APIServerSLZ,
    ClusterRegisterRequestSLZ,
    GenRegionClusterStateSLZ,
    GetClusterComponentStatusSLZ,
    ReadonlyClusterSLZ,
)
from paas_wl.infras.cluster.exceptions import SwitchDefaultClusterError
from paas_wl.infras.cluster.models import APIServer, Cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KSecret
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.networking.egress.cluster_state import generate_state, sync_state_to_nodes
from paasng.infras.accounts.permissions.global_site import SiteAction, site_perm_class

logger = logging.getLogger(__name__)


class ClusterViewSet(mixins.DestroyModelMixin, ReadOnlyModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ReadonlyClusterSLZ
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["region", "name", "is_default"]
    ordering = ("-region",)
    ordering_fields = ("region", "created", "updated")

    @swagger_auto_schema(request_body=ClusterRegisterRequestSLZ)
    def update_or_create(self, request, pk: Optional[str] = None):
        slz = ClusterRegisterRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        cluster = Cluster.objects.register_cluster(**data)
        return Response(data=ReadonlyClusterSLZ(cluster).data)

    def set_as_default(self, request, pk):
        cluster = self.get_object()
        try:
            Cluster.objects.switch_default_cluster(region=cluster.region, cluster_name=cluster.name)
        except SwitchDefaultClusterError as e:
            raise error_codes.SWITCH_DEFAULT_CLUSTER_FAILED.f(str(e))
        return Response()

    @swagger_auto_schema(request_body=APIServerSLZ)
    def bind_api_server(self, request, pk):
        slz = APIServerSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        cluster = self.get_object()
        api_server, _ = APIServer.objects.update_or_create(
            cluster=cluster, host=data["host"], defaults=dict(overridden_hostname=data["overridden_hostname"])
        )
        return Response(data=APIServerSLZ(api_server).data)

    def unbind_api_server(self, request, pk, api_server_id):
        cluster = self.get_object()
        APIServer.objects.filter(cluster=cluster, uuid=api_server_id).delete()
        return Response()

    def gen_node_state(self, request, cluster_name, *args, **kwargs):
        slz = GenRegionClusterStateSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        region = data["region"]

        if not Cluster.objects.filter(region=region, name=cluster_name).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        logger.info(f"will generate state for [{region}/{cluster_name}]...")
        client = get_client_by_cluster_name(cluster_name=cluster_name)

        logger.info(f"generating state for [{region}/{cluster_name}]...")
        state = generate_state(region, cluster_name, client, data["ignore_labels"])

        logger.info("syncing the state to nodes...")
        sync_state_to_nodes(client, state)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterComponentViewSet(ViewSet):
    """集群组件信息相关"""

    def get_operator_info(self, requests, cluster_name, *args, **kwargs):
        """获取各集群 Operator 相关信息"""
        resp_data = {"cluster_name": cluster_name}
        try:
            client = get_client_by_cluster_name(cluster_name)
        except ValueError:
            # 可能存在废弃集群，占位没有删除的情况，这里做兼容处理
            return Response(resp_data)

        # Operator 部署状态
        resp_data.update(detect_operator_status(client))
        # PaaS 平台自定义资源信息
        resp_data.update(fetch_paas_cobj_info(client, resp_data["crds"]))
        return Response(resp_data)

    def list_components(self, request, cluster_name, *args, **kwargs):
        resp_data = {"cluster_name": cluster_name, "components": defaultdict(list)}
        try:
            client = get_client_by_cluster_name(cluster_name)
        except ValueError:
            # 可能存在废弃集群，占位没有删除的情况，这里做兼容处理
            return Response(resp_data)

        secrets = KSecret(client).ops_batch.list({"owner": "helm"}).items
        releases = filter_latest_releases(convert_secrets_to_releases(secrets))

        for rel in releases:
            chart_name = rel.chart.name
            if chart_name not in settings.BKPAAS_K8S_CLUSTER_COMPONENTS:
                continue

            resp_data["components"][chart_name].append(asdict(rel))

        return Response(resp_data)

    def get_component_status(self, request, cluster_name, component_name, *args, **kwargs):
        """查看组件具体状态（主要检查 Workloads 状态）"""
        slz = GetClusterComponentStatusSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        params = slz.validated_data

        try:
            client = get_client_by_cluster_name(cluster_name)
        except ValueError:
            # 可能存在废弃集群，占位没有删除的情况，这里做兼容处理
            return Response()

        try:
            secret = KSecret(client).get(namespace=params["namespace"], name=params["secret_name"])
        except ResourceMissing:
            raise error_codes.CLUSTER_COMPONENT_NOT_EXIST.f(
                "chart {} not deployed in cluster {}".format(cluster_name, component_name)
            )

        release = HelmReleaseParser(secret, parse_manifest=True).parse()
        statuses = WorkloadsDetector(client, release).get_statuses()
        return Response(data=statuses)
