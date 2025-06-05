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

from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from rest_framework import status

from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from tests.paas_wl.utils.wl_app import create_wl_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestClusterNodesStateAPI:
    """测试集群节点状态相关 API"""

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
            cluster_name=cluster_name,
            name=f"state-{created.timestamp()}",
            nodes_name=nodes,
            nodes_cnt=nodes_cnt,
            created=created,
        )
        return state

    def create_mock_app_binding(self, state, app_code):
        """创建模拟的应用绑定关系"""
        app = create_wl_app(paas_app_code=app_code)
        return RCStateAppBinding.objects.create(state=state, app=app)

    def test_list_nodes_state(self, plat_mgt_api_client):
        """测试获取单个最新节点状态"""
        # 创建两个状态记录（最新的节点数更多）
        state1 = self.create_mock_state(self.cluster_name, nodes_cnt=2, created=datetime.now() - timedelta(days=1))
        self.create_mock_app_binding(state1, "app1")

        state2 = self.create_mock_state(self.cluster_name, nodes_cnt=4, created=datetime.now())
        self.create_mock_app_binding(state2, "app2")
        self.create_mock_app_binding(state2, "app3")

        url = reverse("plat_mgt.infras.list_nodes_state", kwargs={"cluster_name": self.cluster_name})
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证返回的是最新记录
        assert len(data["nodes"]) == 4
        assert set(data["binding_apps"]) == {"app2", "app3"}
        assert data["created_at"] is not None

    def test_nodes_sync_records(self, plat_mgt_api_client):
        """测试获取节点同步记录列表"""
        # 创建多个状态记录
        states = []
        for i in range(3):
            state = self.create_mock_state(
                self.cluster_name, nodes_cnt=i + 1, created=datetime.now() - timedelta(days=i)
            )
            self.create_mock_app_binding(state, f"app-{i}")
            states.append(state)

        url = reverse("plat_mgt.infras.nodes_sync_records", kwargs={"cluster_name": self.cluster_name})
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证记录数量
        assert len(data) == 3

        # 验证记录顺序（应该按创建时间倒序）
        assert [record["id"] for record in data] == [s.id for s in reversed(states)]

        # 验证每条记录的基本结构
        for i, record in enumerate(data):
            assert len(record["nodes"]) == 3 - i
            assert record["binding_apps"] == [f"app-{2 - i}"]
            assert record["created_at"] is not None

    def test_invalid_cluster_name(self, plat_mgt_api_client):
        """测试无效集群名称"""

        invalid_cluster_name = "invalid-cluster-name"
        url = reverse("plat_mgt.infras.list_nodes_state", kwargs={"cluster_name": invalid_cluster_name})
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, dict)
        assert data["nodes"] == []
        assert data["created_at"] is None

        special_char_name = "invalid@cluster!name"
        url = reverse("plat_mgt.infras.list_nodes_state", kwargs={"cluster_name": special_char_name})
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["nodes"] == []
        assert data["created_at"] is None
