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
from typing import Optional

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, mixins

from paas_wl.admin.serializers.clusters import (
    APIServerSLZ,
    ClusterRegisterRequestSLZ,
    GenRegionClusterStateSLZ,
    ReadonlyClusterSLZ,
)
from paas_wl.cluster.models import APIServer, Cluster
from paas_wl.networking.egress.models import generate_state
from paas_wl.platform.applications.permissions import SiteAction, site_perm_class
from paas_wl.resources.utils.app import get_scheduler_client

logger = logging.getLogger(__name__)


class ClusterViewSet(mixins.DestroyModelMixin, ReadOnlyModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ReadonlyClusterSLZ
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['region', 'name', 'is_default']
    ordering = ('-region',)
    ordering_fields = ('region', 'created', 'updated')

    @swagger_auto_schema(request_body=ClusterRegisterRequestSLZ)
    def update_or_create(self, request, pk: Optional[str] = None):
        slz = ClusterRegisterRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        cluster = Cluster.objects.register_cluster(**data)
        return Response(data=ReadonlyClusterSLZ(cluster).data)

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

    def gen_state(self, request, *args, **kwargs):
        slz = GenRegionClusterStateSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        cluster_name = data['cluster_name']
        for region in data['regions']:
            clusters = Cluster.objects.filter(region=region)
            # 若已指定集群名称，则只更新对应的集群
            if cluster_name:
                clusters = clusters.filter(name=cluster_name)

            for cluster in clusters:
                logger.info(f'will generate state for [{region}/{cluster.name}]...')
                sched_client = get_scheduler_client(cluster_name=cluster.name)

                logger.info(f'generating state for [{region}/{cluster.name}]...')
                state = generate_state(region, cluster.name, sched_client, data['ignore_labels'])

                logger.info('syncing the state to nodes...')
                sched_client.sync_state_to_nodes(state)

        return Response(status=status.HTTP_204_NO_CONTENT)
