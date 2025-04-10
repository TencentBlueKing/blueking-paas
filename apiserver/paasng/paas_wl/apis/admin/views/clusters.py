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
from collections import defaultdict
from dataclasses import asdict

from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paas_wl.apis.admin.helpers.helm import (
    HelmReleaseParser,
    WorkloadsDetector,
    convert_secrets_to_releases,
    filter_latest_releases,
)
from paas_wl.apis.admin.helpers.operator import detect_operator_status, fetch_paas_cobj_info
from paas_wl.apis.admin.serializers.clusters import (
    GetClusterComponentStatusSLZ,
    ReadonlyClusterSLZ,
)
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KSecret
from paas_wl.utils.error_codes import error_codes
from paasng.infras.accounts.permissions.global_site import SiteAction, site_perm_class

logger = logging.getLogger(__name__)


class ClusterViewSet(GenericViewSet):
    """deprecated：Admin42 功能未来将由平台管理页面替代，目前只保留查看功能"""

    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        clusters = Cluster.objects.all()
        return Response(ReadonlyClusterSLZ(clusters, many=True).data)


class ClusterComponentViewSet(ViewSet):
    """集群组件信息相关"""

    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]

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
