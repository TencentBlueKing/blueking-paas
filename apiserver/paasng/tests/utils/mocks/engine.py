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
"""TestDoubles for paasng.engine module"""
import copy
from contextlib import contextmanager
from typing import Dict, List, Optional
from unittest import mock

import cattr

from paasng.engine.controller.cluster import AbstractRegionClusterService
from paasng.engine.controller.models import Cluster

_faked_cluster_info = {
    "name": "default",
    "is_default": True,
    "bcs_cluster_id": "BCS-K8S-10000",
    "support_bcs_metrics": False,
    "ingress_config": {
        "sub_path_domains": [],
        "app_root_domains": [{"name": "bkapps.example.com"}],
    },
}


class StubRegionClusterService(AbstractRegionClusterService):
    """A mock class without interacting with engine backend"""

    def __init__(self, region: str, cluster_info: Dict):
        self.region = region
        self.cluster_info = cluster_info

    def list_clusters(self) -> List[Cluster]:
        return [cattr.structure(self.cluster_info, Cluster)]

    def get_default_cluster(self) -> Cluster:
        return cattr.structure(self.cluster_info, Cluster)

    def get_cluster(self, name) -> Cluster:
        return cattr.structure(self.cluster_info, Cluster)

    def has_cluster(self, name: str) -> bool:
        return name == self.cluster_info["name"]

    def get_engine_app_cluster(self, engine_app_name: str) -> Cluster:
        return cattr.structure(self.cluster_info, Cluster)

    def set_engine_app_cluster(self, engine_app_name: str, cluster_name: str):
        return


@contextmanager
def replace_cluster_service(ingress_config: Optional[Dict] = None, replaced_ingress_config: Optional[Dict] = None):
    """Replace the original ClusterHelper class to return stubbed instance instead of request engine API

    :param ingress_config: patch default ingress_config
    :param replaced_ingress_config: replace default ingress_config entirely
    """
    cluster_data: Dict = copy.copy(_faked_cluster_info)
    if ingress_config is not None:
        cluster_data['ingress_config'].update(ingress_config)
    if replaced_ingress_config is not None:
        cluster_data['ingress_config'] = replaced_ingress_config

    def _stub_factory(region, *args, **kwargs):
        return StubRegionClusterService(region, cluster_data)

    with mock.patch('paasng.engine.controller.cluster.RegionClusterService', new=_stub_factory):
        yield
