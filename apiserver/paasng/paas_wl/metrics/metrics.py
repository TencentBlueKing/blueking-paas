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

from django.core.cache import cache
from django.utils.timezone import now
from prometheus_client.core import GaugeMetricFamily

from paas_wl.cluster.models import Cluster
from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.resources.base.kube_client import CoreDynamicClient
from paas_wl.workloads.processes.utils import list_unavailable_deployment

logger = logging.getLogger(__name__)


class UnavailableDeploymentTotalMetric:
    name = "unavailable_deployments_total"
    description = "A gauge for counting unavailable deployments"

    @classmethod
    def calc_metric(cls) -> GaugeMetricFamily:
        """获取 metric"""
        cache_key = f"metrics:{cls.name}"
        if v := cache.get(cache_key):
            return v

        dt = now()
        gauge_family = GaugeMetricFamily(
            name=cls.name,
            documentation=cls.description,
            labels=["region", "cluster_name"],
        )
        for cluster in Cluster.objects.all():
            try:
                client = get_client_by_cluster_name(cluster_name=cluster.name)
            except ValueError:
                logger.exception(f"configuration of cluster<{cluster.name}> is not ready")
                continue
            unavailable_deployments = list_unavailable_deployment(CoreDynamicClient(client))
            gauge_family.add_metric(
                labels=[cluster.region, cluster.name],
                value=len(unavailable_deployments),
                timestamp=dt.timestamp(),
            )
        cache.set(cache_key, gauge_family, timeout=60 * 5)
        return gauge_family

    @classmethod
    def describe_metric(cls) -> GaugeMetricFamily:
        """描述 metric"""
        return GaugeMetricFamily(
            name=cls.name,
            documentation=cls.description,
            labels=["region", "cluster_name"],
        )
