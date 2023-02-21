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
"""Cluster related utilities
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from cattr import structure

from paasng.engine.controller.client import ControllerClient
from paasng.engine.controller.models import Cluster
from paasng.engine.controller.shortcuts import make_internal_client
from paasng.platform.core.storages.cache import region as cache_region


class AbstractRegionClusterService(ABC):
    """Abstract class for region cluster"""

    @abstractmethod
    def list_clusters(self) -> List[Cluster]:
        pass

    @abstractmethod
    def get_default_cluster(self) -> Cluster:
        pass

    @abstractmethod
    def get_cluster(self, name: str) -> Cluster:
        pass

    @abstractmethod
    def has_cluster(self, name: str) -> bool:
        pass

    @abstractmethod
    def get_engine_app_cluster(self, engine_app_name: str) -> Cluster:
        pass

    @abstractmethod
    def set_engine_app_cluster(self, engine_app_name: str, cluster_name: str):
        pass


class RegionClusterService(AbstractRegionClusterService):
    """Helper class for region cluster"""

    def __init__(self, region: str, client: Optional[ControllerClient] = None):
        self.region = region
        self.client = client or make_internal_client()

    def list_clusters(self) -> List[Cluster]:
        """List all clusters under region"""
        return structure(self.client.list_region_clusters(self.region), List[Cluster])

    def get_default_cluster(self) -> Cluster:
        """Get default cluster info"""
        for cluster in self.list_clusters():
            if cluster.is_default:
                return cluster
        raise RuntimeError(f'Default cluster not found for {self.region}')

    def get_cluster(self, name: str) -> Cluster:
        """Get cluster by name

        :raises: ValueError when no cluster can be found by given name
        """
        for cluster in self.list_clusters():
            if cluster.name == name:
                return cluster
        raise ValueError(f'Cluster called "{name}" not found in {self.region}')

    def has_cluster(self, name: str) -> bool:
        """Check if there is cluster named {name} under current region"""
        for cluster in self.list_clusters():
            if cluster.name == name:
                return True
        return False

    def get_engine_app_cluster(self, engine_app_name: str) -> Cluster:
        """Get the cluster info of one engine app"""
        config = self.client.retrieve_app_config(self.region, engine_app_name)
        # An empty cluster field means current app uses a default cluster
        if not config['cluster']:
            return self.get_default_cluster()

        clusters = self.list_clusters()
        for cluster in clusters:
            if cluster.name == config["cluster"]:
                return cluster

        raise ValueError('No cluster info found')

    def set_engine_app_cluster(self, engine_app_name: str, cluster_name: str):
        """Set cluster for engine app"""
        self.client.bind_app_cluster(self.region, engine_app_name, cluster_name=cluster_name)


def get_region_cluster_helper(region: str) -> AbstractRegionClusterService:
    """Return a ClusterHelper instance"""
    return RegionClusterService(region)


@cache_region.cache_on_arguments(namespace='v3', expiration_time=60 * 5)
def get_engine_app_cluster(region: str, engine_app_name: str) -> Cluster:
    """Shortcut function for `RegionClusterService.get_engine_app_cluster`"""
    return get_region_cluster_helper(region).get_engine_app_cluster(engine_app_name)
