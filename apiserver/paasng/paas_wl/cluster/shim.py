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
from typing import List, Optional

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.models import Cluster
from paas_wl.networking.egress.misc import ClusterEgressIps, get_cluster_egress_ips
from paas_wl.platform.applications.models import WlApp
from paasng.platform.applications.models import ModuleEnvironment


def get_cluster_egress_info(cluster_name: str) -> ClusterEgressIps:
    """Get cluster's egress info"""
    cluster = Cluster.objects.get(name=cluster_name)
    return get_cluster_egress_ips(cluster)


class RegionClusterService:
    """RegionClusterService provide interface for querying cluster[s] in given region"""

    def __init__(self, region: str):
        self.region = region

    def list_clusters(self) -> List[Cluster]:
        return Cluster.objects.filter(region=self.region)

    def get_default_cluster(self) -> Cluster:
        """获取默认集群"""
        qs = Cluster.objects.filter(region=self.region, is_default=True)
        if qs.exists():
            return qs[0]
        raise Cluster.DoesNotExist(f'Default cluster not found for {self.region}')

    def get_cluster_by_name(self, cluster_name: str) -> Cluster:
        return Cluster.objects.get(region=self.region, name=cluster_name)

    def has_cluster(self, cluster_name: str) -> bool:
        return Cluster.objects.filter(region=self.region, name=cluster_name).exists()


class EnvClusterService:
    """EnvClusterService provide interface for managing the cluster info of given env"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def get_cluster(self) -> Cluster:
        """get the cluster bound to the env, if no specific cluster is bound, return default cluster"""
        return Cluster.objects.get(name=self.get_cluster_name())

    def get_cluster_name(self) -> str:
        """get the cluster bound to the env, if no specific cluster is bound, return default cluster name
        this function will not check if the cluster actually exists.
        """
        wl_app = self.env.wl_app
        if wl_app.latest_config.cluster:
            return wl_app.latest_config.cluster
        return RegionClusterService(self.env.application.region).get_default_cluster().name

    def bind_cluster(self, cluster_name: Optional[str]):
        """bind `env` to cluster named `cluster_name`, if cluster_name is not given, use default cluster

        :raises: Cluster.DoesNotExist if cluster not found
        """
        if cluster_name:
            cluster = Cluster.objects.get(name=cluster_name)
        else:
            cluster = RegionClusterService(self.env.application.region).get_default_cluster()

        wl_app = self.env.wl_app
        _bind_cluster_to_wl_app(wl_app, cluster)


def _bind_cluster_to_wl_app(wl_app: WlApp, cluster: Cluster):
    """bind cluster to wl_app by modifying config.cluster"""
    latest_config = wl_app.latest_config
    latest_config.cluster = cluster.name
    latest_config.mount_log_to_host = cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST)
    latest_config.save()
