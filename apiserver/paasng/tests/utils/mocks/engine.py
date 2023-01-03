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
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
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
        return cattr.structure(self.cluster_info, List[Cluster])

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


class StubControllerClient:
    """Stubbed controller client without calling sending real request"""

    def __init__(self, *args, **kwargs):
        return

    def app__create(self, region, app_name, app_type):
        return {"uuid": str(uuid.uuid4()), "region": region, "name": app_name, "type": app_type}

    def create_cnative_app_model_resource(self, region: str, data: Dict[str, Any]) -> Dict:
        return {
            'application_id': data['application_id'],
            'module_id': data['module_id'],
            'json': {
                'apiVersion': 'paas.bk.tencent.com/v1alpha1',
                'metadata': {'name': data['code']},
                'spec': {
                    'processes': [
                        {
                            'name': 'web',
                            'image': 'nginx:latest',
                            'replicas': 1,
                        }
                    ]
                },
                'kind': 'BkApp',
            },
        }

    def app__delete(self, region, app_name):
        return

    def retrieve_app_config(self, region, app_name):
        return {'cluster': _faked_cluster_info['name'], 'metadata': {}}

    def list_region_clusters(self, region):
        """List region clusters"""
        return [_faked_cluster_info]

    def update_app_metadata(self, region, app_name, payload):
        pass

    def update_app_config(self, region, app_name, payload):
        pass

    def bind_app_cluster(self, region, app_name, cluster_name):
        pass

    def app_proc_ingress_actions__sync(self, region, app_name):
        pass

    def list_env_addresses(self, app_code: str, module_name: str):
        return [
            {'env': 'stag', 'is_running': False, 'addresses': []},
            {'env': 'prod', 'is_running': False, 'addresses': []},
        ]

    def sync_processes_specs(self, region: str, app_name: str, processes: List[Dict]):
        return

    def delete_module_related_res(self, app_code: str, module_name: str):
        return
