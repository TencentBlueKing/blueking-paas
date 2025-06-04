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

from datetime import datetime

import pytest
from django.urls import reverse
from rest_framework import status

from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from tests.paas_wl.utils.wl_app import create_wl_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestClusterNodesInfoViewSet:
    """测试集群节点信息 API"""

    @pytest.fixture(autouse=True)
    def _setup(self, settings):
        self.cluster_name = "test-cluster"
        RegionClusterState.objects.all().delete()
        RCStateAppBinding.objects.all().delete()

    def create_mock_state(self, cluster_name, nodes_cnt=0, nodes=None, created=None):
        """创建模拟的 RegionClusterState 对象"""
        if nodes is None:
            nodes = [f"node-{i}" for i in range(nodes_cnt)]

        if created is None:
            created = datetime.now()

        state = RegionClusterState.objects.create(
            cluster_name=cluster_name, nodes_name=nodes, nodes_cnt=nodes_cnt, created=created
        )
        return state

    def _create_mock_state(self, nodes_cnt=3, created=None):
        """创建模拟的集群状态数据"""
        if created is None:
            created = datetime.now()

        # 确保name字段唯一
        state = RegionClusterState.objects.create(
            cluster_name=self.cluster_name,
            name=f"state-{created.timestamp()}",
            nodes_name=[f"node-{i}" for i in range(nodes_cnt)],
            nodes_cnt=nodes_cnt,
            created=created,
        )

        # 创建两个应用并绑定到集群状态
        app1 = create_wl_app(paas_app_code="app-1")
        app2 = create_wl_app(paas_app_code="app-2")
        RCStateAppBinding.objects.create(state=state, app=app1)
        RCStateAppBinding.objects.create(state=state, app=app2)
        return state

    def test_list_nodes_info_with_data(self, plat_mgt_api_client):
        self._create_mock_state()

        url = reverse("plat_mgt.infras.cluster_nodes_info.list")
        resp = plat_mgt_api_client.get(url, {"cluster_name": self.cluster_name})

        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        assert len(result["nodes"]) == 3
        assert set(result["binding_apps"]) == {"app-1", "app-2"}
        assert result["created_at"] is not None

    def test_list_sync_records_with_data(self, plat_mgt_api_client):
        self._create_mock_state()

        url = reverse("plat_mgt.infras.cluster_sync_records.list")
        resp = plat_mgt_api_client.get(url, {"cluster_name": self.cluster_name})

        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        assert len(result["nodes"]) == 3
        assert set(result["binding_apps"]) == {"app-1", "app-2"}
        assert result["nodes_cnt"] == 3
        assert result["created_at"] is not None

    def test_invalid_cluster_name(self, plat_mgt_api_client):
        url = reverse("plat_mgt.infras.cluster_nodes_info.list")
        resp = plat_mgt_api_client.get(url, {"cluster_name": ""})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        response_data = resp.json()
        assert "detail" in response_data or "cluster_name" in response_data
