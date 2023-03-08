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
from blue_krill.connections.exceptions import NoEndpointAvailable
from django.test import TestCase

from paas_wl.cluster.pools import ContextConfigurationPoolMap
from paas_wl.resources.base.client import K8sScheduler
from tests.conftest import CLUSTER_NAME_FOR_TESTING


class TestPresetClient(TestCase):
    """由于 preset client 只是在 configuration 读取 & failover 上有差异
    所以在这里测试
    """

    def setUp(self) -> None:
        self.client = K8sScheduler.from_cluster_name(cluster_name=CLUSTER_NAME_FOR_TESTING)

    def test_call_api(self):
        result = self.client.get_nodes()
        assert isinstance(result, list)

    def call_api_all_failed(self):
        """在恢复机制不够完善之前暂时不启用隔离"""
        _k8s_global_configuration_pool_map = ContextConfigurationPoolMap.from_file(
            "tests/assets/example-kube-config.yaml"
        )
        # 为了更快能够隔离所有节点，选择 host 最少的
        client = K8sScheduler.from_cluster_name(cluster_name="40005")
        client.client.configuration_pool = _k8s_global_configuration_pool_map["40005"]
        client.client.configuration_pool.algorithm.unhealthy_max_failed = 1
        with self.assertRaises(NoEndpointAvailable):
            client.get_nodes()
