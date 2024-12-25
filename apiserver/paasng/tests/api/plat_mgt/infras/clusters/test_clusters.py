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
from typing import Any, Dict
from unittest.mock import patch

import cattrs
import pytest
from attr import define, field
from django.urls import reverse
from rest_framework import status

from paas_wl.infras.cluster.constants import (
    ClusterAllocationPolicyCondType,
    ClusterAllocationPolicyType,
    ClusterFeatureFlag,
)
from paas_wl.infras.cluster.entities import AllocationRule, IngressConfig
from paas_wl.infras.cluster.models import Cluster, ClusterAllocationPolicy
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.platform.applications.constants import AppEnvironment
from tests.paas_wl.utils.wl_app import create_wl_app
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

# TODO（多租户）单元测试补充租户管理员场景，目前只有平台管理员的


class TestListClusters:
    """获取集群列表"""

    def test_list(self, init_default_cluster, init_system_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(reverse("plat_mgt.infras.cluster.bulk"))
        assert resp.status_code == status.HTTP_200_OK

        assert len(resp.json()) >= 2

        cluster = [c for c in resp.json() if c["name"] == init_default_cluster.name][0]
        assert cluster == {
            "name": init_default_cluster.name,
            "bcs_cluster_id": "BCS-K8S-00000",
            "description": "default tenant cluster",
            "tenant": "default",
            "available_tenants": ["default"],
            "feature_flags": [
                "支持提供出口 IP",
                "允许挂载日志到主机",
                "支持蓝鲸监控",
                "使用蓝鲸日志平台方案采集日志",
                "支持自动扩容",
                "支持 BCS Egress",
            ],
            "nodes": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
        }


class TestRetrieveCluster:
    """获取集群详情"""

    def test_retrieve(self, init_system_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.detail",
                kwargs={"cluster_name": init_system_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_200_OK

        assert resp.json() == {
            "name": init_system_cluster.name,
            "description": "op tenant cluster",
            "cluster_source": "native_k8s",
            "bcs_project_id": None,
            "bcs_cluster_id": None,
            "bk_biz_id": None,
            "api_servers": [
                "http://127.0.0.8:6553",
                "http://127.0.0.9:6553",
            ],
            "auth_type": "cert",
            "ca": "*******",
            "cert": "*******",
            "key": "*******",
            "token": "*******",
            "container_log_dir": "/var/lib/docker/containers",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "https",
                "host": "127.0.0.12",
                "port": 9200,
                "username": "blueking",
                "password": "*******",
            },
            "available_tenant_ids": ["system", "default"],
            "node_selector": {},
            "tolerations": [],
            "feature_flags": {
                ClusterFeatureFlag.ENABLE_EGRESS_IP: False,
                ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: True,
                ClusterFeatureFlag.INGRESS_USE_REGEX: False,
                ClusterFeatureFlag.ENABLE_BK_MONITOR: True,
                ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR: True,
                ClusterFeatureFlag.ENABLE_AUTOSCALING: False,
                ClusterFeatureFlag.ENABLE_BCS_EGRESS: False,
            },
        }


class TestCreateCluster:
    """创建集群"""

    def test_create_cluster_from_bcs(self, plat_mgt_api_client):
        """基于 bcs 集群创建集群"""

        cluster_name = generate_random_string(length=8)
        data = {
            "name": cluster_name,
            "description": "test_bcs_cluster",
            "cluster_source": "bcs",
            "bcs_project_id": "8470abd6fe455ca",
            "bcs_cluster_id": "BCS-K8S-00000",
            "bk_biz_id": "12345",
            "api_servers": ["http://bcs-api.example.com/clusters/BCS-K8S-00000"],
            "auth_type": "token",
            "token": generate_random_string(32),
            # bcs 集群其实不需要证书，这里为了测试不会保留无效数据
            "ca": "MTIzNDU2Cg==",
            "cert": "MTIzNDU2Cg==",
            "key": "MTIzNDU2Cg==",
            "container_log_dir": "/var/lib/docker/containers/",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.1",
                "port": "9300",
                "username": "admin",
                "password": "masked",
            },
            "available_tenant_ids": ["cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.bulk"), data=data)

        assert resp.status_code == status.HTTP_201_CREATED

        cluster = Cluster.objects.filter(name=cluster_name).first()
        assert cluster is not None

        assert cluster.annotations == {
            "bcs_project_id": "8470abd6fe455ca",
            "bcs_cluster_id": "BCS-K8S-00000",
            "bk_biz_id": "12345",
        }
        assert len(cluster.token_value) == 32
        assert cluster.ca_data is None
        assert cluster.cert_data is None
        assert cluster.key_data is None
        assert cluster.ingress_config == IngressConfig(frontend_ingress_ip="127.0.0.1")
        assert cluster.container_log_dir == "/var/lib/docker/containers/"

        assert cluster.api_servers.count() == 1
        assert cluster.api_servers.first().host == "http://bcs-api.example.com/clusters/BCS-K8S-00000"

        assert cluster.elastic_search_config is not None
        assert cluster.elastic_search_config.port == 9300
        assert cluster.elastic_search_config.password == "masked"

    def test_create_cluster_from_bcs_without_annotations(self, plat_mgt_api_client):
        """基于 bcs 集群创建集群"""
        data = {
            "name": generate_random_string(length=8),
            "description": "test_bcs_cluster",
            "cluster_source": "bcs",
            "bcs_project_id": "",
            "bcs_cluster_id": None,
            "api_servers": ["http://bcs-api.example.com/clusters/BCS-K8S-00000"],
            "auth_type": "token",
            "token": generate_random_string(32),
            "container_log_dir": "/var/lib/docker/containers/",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.1",
                "port": "9300",
                "username": "admin",
                "password": "masked",
            },
            "available_tenant_ids": ["cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.bulk"), data=data)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "BCS 集群必须提供项目，集群，业务信息" in resp.json()["detail"]

    def test_create_cluster_from_native_k8s(self, plat_mgt_api_client):
        """基于原生 k8s 集群创建集群"""
        cluster_name = generate_random_string(length=8)
        data = {
            "name": cluster_name,
            "description": "test_bcs_cluster",
            "cluster_source": "native_k8s",
            "api_servers": [
                "http://127.0.0.1:6553",
                "http://127.0.0.2:6553",
                "http://127.0.0.3:6553",
            ],
            "auth_type": "cert",
            "token": generate_random_string(32),
            # bcs 集群其实不需要证书，这里为了测试不会保留无效数据
            "ca": "MTIzNDU2Cg==",
            "cert": "MTIzNDU2Cg==",
            "key": "MTIzNDU2Cg==",
            "container_log_dir": "/var/lib/docker/containers/",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.1",
                "port": "9300",
                "username": "admin",
                "password": "masked",
            },
            "available_tenant_ids": ["cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.bulk"), data=data)

        assert resp.status_code == status.HTTP_201_CREATED

        cluster = Cluster.objects.filter(name=cluster_name).first()
        assert cluster is not None

        assert cluster.annotations == {}
        assert cluster.token_value is None
        assert cluster.ca_data is not None
        assert cluster.cert_data is not None
        assert cluster.key_data is not None

        assert cluster.api_servers.count() == 3
        assert set(cluster.api_servers.values_list("host", flat=True)) == {
            "http://127.0.0.1:6553",
            "http://127.0.0.2:6553",
            "http://127.0.0.3:6553",
        }

    def test_create_cluster_from_native_k8s_without_cert(self, plat_mgt_api_client):
        """基于原生 k8s 集群创建集群"""
        data = {
            "name": generate_random_string(length=8),
            "description": "test_bcs_cluster",
            "cluster_source": "native_k8s",
            "api_servers": [
                "http://127.0.0.1:6553",
                "http://127.0.0.2:6553",
                "http://127.0.0.3:6553",
            ],
            "auth_type": "cert",
            "ca": "",
            "container_log_dir": "/var/lib/docker/containers/",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.1",
                "port": "9300",
                "username": "admin",
                "password": "masked",
            },
            "available_tenant_ids": ["cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.bulk"), data=data)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "集群认证方式为证书时，CA 证书 + 证书 + 私钥 必须同时提供" in resp.json()["detail"]


class TestUpdateCluster:
    """更新集群"""

    def test_update_cluster_access(self, init_system_cluster, plat_mgt_api_client):
        """集群更新 - 集群接入（第一步场景）"""

    def test_update_cluster_component(self, init_system_cluster, plat_mgt_api_client):
        """集群更新 - 集群组件（第二步场景）"""

    def test_update_feature_flags(self, init_system_cluster, plat_mgt_api_client):
        """集群更新 - 集群特性（第三步场景）"""


class TestDeleteCluster:
    """删除集群"""

    def test_delete_cluster(self, init_system_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.delete(
            reverse("plat_mgt.infras.cluster.detail", kwargs={"cluster_name": init_system_cluster.name})
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_cluster_allocation_policy_exists(self, init_system_cluster, plat_mgt_api_client):
        ClusterAllocationPolicy.objects.create(
            tenant_id=OP_TYPE_TENANT_ID,
            type=ClusterAllocationPolicyType.STATIC,
            rules=[AllocationRule(env_specific=False, clusters=[init_system_cluster.name])],
        )
        resp = plat_mgt_api_client.delete(
            reverse("plat_mgt.infras.cluster.detail", kwargs={"cluster_name": init_system_cluster.name})
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "集群已被租户 system 分配" in resp.json()["detail"]

    def test_delete_cluster_wl_app_bind(self, init_system_cluster, plat_mgt_api_client):
        create_wl_app(
            paas_app_code=generate_random_string(8),
            environment=AppEnvironment.STAGING,
            cluster_name=init_system_cluster.name,
        )
        resp = plat_mgt_api_client.delete(
            reverse("plat_mgt.infras.cluster.detail", kwargs={"cluster_name": init_system_cluster.name})
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "集群已被 1 个应用部署环境绑定" in resp.json()["detail"]


class TestRetrieveClusterStatus:
    """获取集群状态"""

    # TODO（多租户）支持获取集群配置 & 组件状态


class TestRetrieveClusterUsage:
    """获取集群使用情况"""

    def test_retrieve_usage(self, bk_cnative_app, init_system_cluster, init_default_cluster, plat_mgt_api_client):
        ClusterAllocationPolicy.objects.create(
            tenant_id=DEFAULT_TENANT_ID,
            type=ClusterAllocationPolicyType.RULE,
            rules=[
                AllocationRule(
                    env_specific=True,
                    matcher={ClusterAllocationPolicyCondType.REGION_IS: "default"},
                    env_clusters={
                        AppEnvironment.STAGING: [init_system_cluster.name],
                        AppEnvironment.PRODUCTION: [init_system_cluster.name, init_default_cluster.name],
                    },
                ),
            ],
        )
        app_code = generate_random_string(8)
        create_wl_app(
            paas_app_code=app_code,
            environment=AppEnvironment.STAGING,
            cluster_name=init_system_cluster.name,
        )

        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.usage",
                kwargs={"cluster_name": init_system_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {
            "available_tenant_ids": ["system", "default"],
            "allocated_tenant_ids": ["default"],
            "bind_app_module_envs": [
                {
                    "app_code": app_code,
                    "module_name": "default",
                    "environment": "stag",
                }
            ],
        }


class TestSyncClusterNodes:
    """同步集群节点"""

    @pytest.fixture(autouse=True)
    def _patch_get_nodes(self):
        @define
        class Metadata:
            name: str
            labels: Dict[str, str] = field(factory=dict)

            def get(self, key, default=None):
                return getattr(self, key, default)

        @define
        class Node:
            metadata: Metadata
            status: Dict[str, Any] = field(factory=dict)

            def to_dict(self):
                return cattrs.unstructure(self)

        with patch(
            "paas_wl.workloads.networking.egress.cluster_state.get_nodes",
            return_value=[Node(metadata=Metadata(name=name)) for name in ["127.0.0.11", "127.0.0.12", "127.0.0.13"]],
        ), patch(
            "paasng.plat_mgt.infras.clusters.views.clusters.sync_state_to_nodes",
            return_value=None,
        ):
            yield

    def test_sync_cluster_nodes(self, init_system_cluster, plat_mgt_api_client):
        url = reverse(
            "plat_mgt.infras.cluster.sync_nodes",
            kwargs={"cluster_name": init_system_cluster.name},
        )
        resp = plat_mgt_api_client.post(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert RegionClusterState.objects.filter(cluster_name=init_system_cluster.name).count() == 2
