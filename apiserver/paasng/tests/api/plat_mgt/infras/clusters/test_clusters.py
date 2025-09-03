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
from typing import Any, Dict
from unittest import mock
from unittest.mock import patch

import cattrs
import pytest
from attr import define, field
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from paas_wl.infras.cluster.constants import (
    ClusterAllocationPolicyCondType,
    ClusterAllocationPolicyType,
    ClusterFeatureFlag,
)
from paas_wl.infras.cluster.entities import Domain, IngressConfig
from paas_wl.infras.cluster.models import Cluster
from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.modules.constants import ExposedURLType
from tests.paas_wl.utils.wl_app import create_wl_app
from tests.utils.basic import generate_random_string
from tests.utils.mocks.helm import StubHelmClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

# TODO（多租户）单元测试补充租户管理员场景，目前只有平台管理员的


class TestListClusters:
    """获取集群列表"""

    def test_list(self, init_default_cluster, init_system_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(reverse("plat_mgt.infras.cluster.list_create"))
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
                "允许挂载日志到主机",
                "从蓝鲸监控查询资源使用率",
                "使用蓝鲸日志平台方案采集日志",
                "支持自动扩容",
                "支持 BCS Egress",
            ],
            "nodes": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
        }


class TestRetrieveCluster:
    """获取集群详情"""

    def test_retrieve(self, init_system_cluster, plat_mgt_api_client, random_tenant_id):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.retrieve_update_destroy",
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
            "bcs_project_name": "",
            "bcs_cluster_name": "",
            "bk_biz_name": "",
            "api_address_type": "custom",
            "api_servers": [
                "http://127.0.0.8:6553",
                "http://127.0.0.9:6553",
            ],
            "auth_type": "cert",
            "container_log_dir": "/var/lib/docker/containers",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "https",
                "host": "127.0.0.12",
                "port": 9200,
                "username": "blueking",
                "password": "blueking",
                "verify_certs": False,
                "ca_certs": None,
                "client_cert": None,
                "client_key": None,
            },
            "app_image_registry": {
                "host": "hub.bktencent.com",
                "skip_tls_verify": False,
                "namespace": "bkapps",
                "username": "blueking",
                "password": "blueking",
            },
            "available_tenant_ids": ["system", "default", random_tenant_id],
            "app_address_type": "subdomain",
            "app_domains": [
                {
                    "https_enabled": False,
                    "name": "bkapps.example.com",
                    "reserved": False,
                }
            ],
            "component_image_registry": "hub.bktencent.com",
            "component_preferred_namespace": "blueking",
            "node_selector": {},
            "tolerations": [],
            "feature_flags": {
                ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: True,
                ClusterFeatureFlag.INGRESS_USE_REGEX: False,
                ClusterFeatureFlag.ENABLE_BK_MONITOR: True,
                ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR: True,
                ClusterFeatureFlag.ENABLE_AUTOSCALING: False,
                ClusterFeatureFlag.ENABLE_BCS_EGRESS: False,
            },
            "ca": "MTIzNDU2Cg==",
            "cert": "MTIzNDU2Cg==",
            "key": "MTIzNDU2Cg==",
            "token": None,
        }

    def test_retrieve_bcs_cluster(self, init_default_cluster, plat_mgt_api_client, random_tenant_id):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.retrieve_update_destroy",
                kwargs={"cluster_name": init_default_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_200_OK

        assert resp.json() == {
            "name": init_default_cluster.name,
            "description": "default tenant cluster",
            "cluster_source": "bcs",
            "bcs_project_id": "abcdef012345",
            "bcs_cluster_id": "BCS-K8S-00000",
            "bk_biz_id": "12345",
            "bcs_project_name": "",
            "bcs_cluster_name": "",
            "bk_biz_name": "",
            "api_address_type": "bcs_gateway",
            "api_servers": [
                "http://bcs-api.example.com/clusters/BCS-K8S-00000",
            ],
            "auth_type": "token",
            "container_log_dir": "/var/lib/docker/containers",
            "access_entry_ip": "127.0.0.1",
            "elastic_search_config": {
                "scheme": "https",
                "host": "127.0.0.11",
                "port": 9200,
                "username": "admin",
                "password": "admin",
                "verify_certs": False,
                "ca_certs": None,
                "client_cert": None,
                "client_key": None,
            },
            "app_image_registry": None,
            "available_tenant_ids": ["default"],
            "app_address_type": "subpath",
            "app_domains": [
                {
                    "https_enabled": False,
                    "name": "bkapps.example.com",
                    "reserved": False,
                }
            ],
            "component_image_registry": "hub.bktencent.com",
            "component_preferred_namespace": "blueking",
            "node_selector": {},
            "tolerations": [],
            "feature_flags": {
                ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: True,
                ClusterFeatureFlag.INGRESS_USE_REGEX: False,
                ClusterFeatureFlag.ENABLE_BK_MONITOR: True,
                ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR: True,
                ClusterFeatureFlag.ENABLE_AUTOSCALING: True,
                ClusterFeatureFlag.ENABLE_BCS_EGRESS: True,
            },
            "ca": None,
            "cert": None,
            "key": None,
            "token": "masked",
        }


class TestCreateCluster:
    """创建集群"""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=True),
            mock.patch("paasng.plat_mgt.infras.clusters.views.clusters.check_k8s_accessible", return_value=True),
        ):
            yield

    def test_create_cluster_from_bcs(self, plat_mgt_api_client):
        """基于 bcs 集群创建集群"""

        cluster_name = generate_random_string(length=8)
        data = {
            "name": cluster_name,
            "description": "test_bcs_cluster",
            "cluster_source": "bcs",
            "bcs_project_id": "abcdef012345",
            "bcs_cluster_id": "BCS-K8S-00000",
            "bk_biz_id": "12345",
            "api_address_type": "bcs_gateway",
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
            "app_image_registry": {
                "host": "hub.bktencent.com",
                "skip_tls_verify": False,
                "namespace": "bkapps",
                "username": "admin",
                "password": "masked",
            },
            "available_tenant_ids": [OP_TYPE_TENANT_ID, "cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.list_create"), data=data)
        assert resp.status_code == status.HTTP_201_CREATED

        cluster = Cluster.objects.filter(name=cluster_name).first()
        assert cluster is not None

        assert cluster.annotations == {
            "bcs_project_id": "abcdef012345",
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
        # ES 未传 TLS 配置时使用默认值
        assert cluster.elastic_search_config.verify_certs is False
        assert cluster.elastic_search_config.ca_certs is None
        assert cluster.elastic_search_config.client_cert is None

        assert cluster.app_image_registry is not None
        assert cluster.app_image_registry.host == "hub.bktencent.com"
        assert cluster.app_image_registry.namespace == "bkapps"
        assert cluster.app_image_registry.username == "admin"
        assert cluster.app_image_registry.password == "masked"

    def test_create_cluster_from_bcs_without_annotations(self, plat_mgt_api_client):
        """基于 bcs 集群创建集群"""
        data = {
            "name": generate_random_string(length=8),
            "description": "test_bcs_cluster",
            "cluster_source": "bcs",
            "bcs_project_id": "",
            "bcs_cluster_id": None,
            "api_address_type": "bcs_gateway",
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
            "available_tenant_ids": [OP_TYPE_TENANT_ID, "cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.list_create"), data=data)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "BCS 集群必须提供项目，集群，业务信息" in resp.json()["detail"]

    def test_create_cluster_from_native_k8s(self, plat_mgt_api_client):
        """基于原生 k8s 集群创建集群"""
        cluster_name = generate_random_string(length=8)
        data = {
            "name": cluster_name,
            "description": "test_bcs_cluster",
            "cluster_source": "native_k8s",
            "api_address_type": "custom",
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
            # 注：默认 / 运营租户不提供 AppImageRegistry 也是可以的
            "available_tenant_ids": [OP_TYPE_TENANT_ID, "cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.list_create"), data=data)
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
            "api_address_type": "custom",
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
            "available_tenant_ids": [OP_TYPE_TENANT_ID, "cobra", "viper"],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster.list_create"), data=data)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "集群认证方式为证书时，CA 证书 + 证书 + 私钥 必须同时提供" in resp.json()["detail"]


class TestUpdateCluster:
    """更新集群"""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=True),
            mock.patch("paasng.plat_mgt.infras.clusters.views.clusters.check_k8s_accessible", return_value=True),
        ):
            yield

    def test_update_scene_cluster_access(self, init_default_cluster, plat_mgt_api_client):
        """集群更新 - 集群接入（第一步场景）"""
        data = {
            "name": init_default_cluster.name,
            "description": generate_random_string(64),
            # bcs 集群改成原生 k8s 集群
            "cluster_source": "native_k8s",
            "api_address_type": "custom",
            "api_servers": [
                "http://127.0.0.1:6553",
                "http://127.0.0.2:6553",
                "http://127.0.0.3:6553",
            ],
            "auth_type": "cert",
            "ca": "MTIzNDU2Cg==",
            "cert": "MTIzNDU2Cg==",
            "key": "MTIzNDU2Cg==",
            "app_address_type": "subdomain",
            "app_domains": [
                {
                    "https_enabled": True,
                    "name": "bkapps-sz1.example.com",
                    "reserved": True,
                }
            ],
            "container_log_dir": "/var/lib/containerd",
            "access_entry_ip": "127.0.0.11",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.10",
                "port": "9000",
                "username": "admin",
                "password": "admin123",
            },
            "available_tenant_ids": [DEFAULT_TENANT_ID, "cobra", "viper"],
            "component_image_registry": "hub.tencent.com",
            "component_preferred_namespace": "blueking",
            "feature_flags": init_default_cluster.feature_flags,
        }
        url = reverse(
            "plat_mgt.infras.cluster.retrieve_update_destroy",
            kwargs={"cluster_name": init_default_cluster.name},
        )
        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        init_default_cluster.refresh_from_db()
        assert init_default_cluster.token_value is None
        assert init_default_cluster.container_log_dir == "/var/lib/containerd"
        assert init_default_cluster.exposed_url_type == ExposedURLType.SUBDOMAIN
        assert init_default_cluster.ingress_config.app_root_domains == [
            Domain(name="bkapps-sz1.example.com", https_enabled=True, reserved=True)
        ]
        # 旧的域名配置（子路径）也会被保留
        assert init_default_cluster.ingress_config.sub_path_domains == [
            Domain(name="bkapps.example.com", https_enabled=False, reserved=False)
        ]
        assert init_default_cluster.ingress_config.frontend_ingress_ip == "127.0.0.11"
        assert init_default_cluster.elastic_search_config.password == "admin123"

    def test_update_scene_cluster_component(self, init_default_cluster, plat_mgt_api_client):
        """集群更新 - 集群组件（第二步场景）"""
        data = {
            "name": init_default_cluster.name,
            "description": generate_random_string(64),
            "cluster_source": "bcs",
            "bcs_project_id": "fake_project_id",
            "bcs_cluster_id": "BCS-K8S-55555",
            "bk_biz_id": "54321",
            "api_address_type": "bcs_gateway",
            "api_servers": [
                "http://bcs-api.example.com/clusters/BCS-K8S-55555",
            ],
            "auth_type": "token",
            "token": "blueking123456",
            "container_log_dir": "/var/lib/containerd",
            "access_entry_ip": "127.0.0.11",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.10",
                "port": "9000",
                "username": "admin",
                "password": "admin",
            },
            "available_tenant_ids": [DEFAULT_TENANT_ID, "cobra", "viper"],
            "component_image_registry": "hub.bk.tencent.com",
            "component_preferred_namespace": "blueking-system",
            "feature_flags": init_default_cluster.feature_flags,
        }
        url = reverse(
            "plat_mgt.infras.cluster.retrieve_update_destroy",
            kwargs={"cluster_name": init_default_cluster.name},
        )
        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        init_default_cluster.refresh_from_db()
        assert init_default_cluster.token_value == "blueking123456"
        assert init_default_cluster.annotations == {
            "bcs_project_id": "fake_project_id",
            "bcs_cluster_id": "BCS-K8S-55555",
            "bk_biz_id": "54321",
        }
        assert init_default_cluster.api_servers.filter(host__icontains="55555").exists()
        assert init_default_cluster.component_image_registry == "hub.bk.tencent.com"
        assert init_default_cluster.component_preferred_namespace == "blueking-system"
        # 不提交 password 不会覆盖原来数据库中的值
        assert init_default_cluster.elastic_search_config.password == "admin"

    def test_update_scene_feature_flags(self, init_system_cluster, init_default_cluster, plat_mgt_api_client):
        """集群更新 - 集群特性（第三步场景）"""
        data = {
            "name": init_system_cluster.name,
            "description": generate_random_string(64),
            "cluster_source": "native_k8s",
            "api_address_type": "custom",
            "api_servers": [
                "http://127.0.0.18:6553",
                "http://127.0.0.19:6553",
            ],
            "auth_type": "cert",
            "ca": "MTIzXDU2Cg==",
            "cert": "MTIzXDU2Cg==",
            "key": "MTIzXDU2Cg==",
            "container_log_dir": "/var/lib/containerd",
            "access_entry_ip": "127.0.0.11",
            "elastic_search_config": {
                "scheme": "http",
                "host": "127.0.0.10",
                "port": "9000",
                "username": "admin",
                "password": "admin1234",
            },
            "available_tenant_ids": [OP_TYPE_TENANT_ID, "cobra", "viper"],
            "component_image_registry": "bk.tencent.com",
            "component_preferred_namespace": "blueking",
            "feature_flags": init_default_cluster.feature_flags,
            "node_selector": {"paas.bk.tencent.com/node-type": "saas"},
            "tolerations": [
                {
                    "key": "paas.bk.tencent.com/node-type",
                    "operator": "Equal",
                    "value": "nginx",
                    "effect": "PreferNoSchedule",
                }
            ],
        }
        url = reverse(
            "plat_mgt.infras.cluster.retrieve_update_destroy",
            kwargs={"cluster_name": init_system_cluster.name},
        )
        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        init_system_cluster.refresh_from_db()
        assert init_system_cluster.ca_data == "MTIzXDU2Cg=="
        assert init_system_cluster.cert_data == "MTIzXDU2Cg=="
        assert init_system_cluster.key_data == "MTIzXDU2Cg=="
        assert init_system_cluster.annotations == {}
        assert set(init_system_cluster.api_servers.values_list("host", flat=True)) == {
            "http://127.0.0.18:6553",
            "http://127.0.0.19:6553",
        }
        assert init_system_cluster.feature_flags == init_default_cluster.feature_flags
        assert init_system_cluster.default_node_selector != []
        assert init_system_cluster.default_tolerations != []


class TestDeleteCluster:
    """删除集群"""

    def test_delete_cluster(self, init_system_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.delete(
            reverse(
                "plat_mgt.infras.cluster.retrieve_update_destroy",
                kwargs={"cluster_name": init_system_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_cluster_when_allocation_policy_exists(self, init_system_cluster, plat_mgt_api_client):
        data = {
            "tenant_id": OP_TYPE_TENANT_ID,
            "type": ClusterAllocationPolicyType.UNIFORM,
            "allocation_policy": {"env_specific": False, "clusters": [init_system_cluster.name]},
        }
        # 使用创建 API 初始化集群分配策略
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster_allocation_policy.list_create"), data=data)
        assert resp.status_code == status.HTTP_201_CREATED

        resp = plat_mgt_api_client.delete(
            reverse(
                "plat_mgt.infras.cluster.retrieve_update_destroy",
                kwargs={"cluster_name": init_system_cluster.name},
            )
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
            reverse(
                "plat_mgt.infras.cluster.retrieve_update_destroy",
                kwargs={"cluster_name": init_system_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "集群已被 1 个应用部署环境绑定" in resp.json()["detail"]


class TestRetrieveClusterStatus:
    """获取集群状态"""

    @pytest.fixture(autouse=True)
    def _patch_helm_client(self):
        with patch("paasng.plat_mgt.infras.clusters.views.clusters.HelmClient", new=StubHelmClient):
            yield

    def test_retrieve(self, init_default_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.status",
                kwargs={"cluster_name": init_default_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_200_OK

        assert resp.json() == {"basic": True, "component": False, "feature": True}


class TestRetrieveClusterUsage:
    """获取集群使用情况"""

    def test_retrieve_usage(
        self,
        bk_cnative_app,
        init_system_cluster,
        init_default_shared_cluster,
        random_tenant_id,
        plat_mgt_api_client,
    ):
        data = {
            "tenant_id": OP_TYPE_TENANT_ID,
            "type": ClusterAllocationPolicyType.RULE_BASED,
            "allocation_precedence_policies": [
                {
                    "matcher": {ClusterAllocationPolicyCondType.REGION_IS: "default"},
                    "policy": {
                        "env_specific": True,
                        "env_clusters": {
                            AppEnvironment.STAGING: [init_system_cluster.name],
                            AppEnvironment.PRODUCTION: [init_system_cluster.name, init_default_shared_cluster.name],
                        },
                    },
                },
                {
                    "policy": {"env_specific": False, "clusters": [init_system_cluster.name]},
                },
            ],
        }
        # 使用创建 API 初始化集群分配策略
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster_allocation_policy.list_create"), data=data)
        assert resp.status_code == status.HTTP_201_CREATED
        # 初始化 wl_app 并绑定集群
        app_code = generate_random_string(8)
        create_wl_app(
            paas_app_code=app_code,
            environment=AppEnvironment.STAGING,
            cluster_name=init_system_cluster.name,
        )

        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.allocation_state",
                kwargs={"cluster_name": init_system_cluster.name},
            )
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {
            "available_tenant_ids": ["system", "default", random_tenant_id],
            "allocated_tenant_ids": ["system"],
            "bound_app_module_envs": [
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

        with (
            patch(
                "paas_wl.workloads.networking.egress.cluster_state.get_nodes",
                return_value=[
                    Node(metadata=Metadata(name=name)) for name in ["127.0.0.11", "127.0.0.12", "127.0.0.13"]
                ],
            ),
            patch(
                "paasng.plat_mgt.infras.clusters.views.clusters.sync_state_to_nodes",
                return_value=None,
            ),
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


class TestClusterNodesState:
    """集群节点状态"""

    @pytest.fixture(autouse=True)
    def _setup(self, settings):
        self.cluster_name = "test-cluster"
        RegionClusterState.objects.all().delete()
        RCStateAppBinding.objects.all().delete()

    def _create_state(self, cluster_name, nodes_cnt=0, nodes=None, created=None):
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

    def _create_app_binding(self, state, app_code):
        app = create_wl_app(paas_app_code=app_code)
        return RCStateAppBinding.objects.create(state=state, app=app)

    def test_retrieve_nodes_state(self, plat_mgt_api_client):
        state1 = self._create_state(self.cluster_name, nodes_cnt=2, created=datetime.now() - timedelta(days=1))
        self._create_app_binding(state1, "app1")

        state2 = self._create_state(self.cluster_name, nodes_cnt=4, created=datetime.now())
        self._create_app_binding(state2, "app2")
        self._create_app_binding(state2, "app3")

        url = reverse("plat_mgt.infras.cluster.retrieve_nodes_state", kwargs={"cluster_name": self.cluster_name})
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["nodes"]) == 4
        assert set(data["binding_apps"]) == {"app2", "app3"}
        assert data["created_at"] is not None

    def test_retrieve_nodes_sync_records(self, plat_mgt_api_client):
        states = []
        for i in range(3):
            state = self._create_state(self.cluster_name, nodes_cnt=i + 1, created=datetime.now() - timedelta(days=i))
            self._create_app_binding(state, f"app-{i}")
            states.append(state)

        url = reverse(
            "plat_mgt.infras.cluster.retrieve_nodes_sync_records", kwargs={"cluster_name": self.cluster_name}
        )
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 3

        assert [record["id"] for record in data] == [s.id for s in reversed(states)]

        for i, record in enumerate(data):
            assert len(record["nodes"]) == 3 - i
            assert record["binding_apps"] == [f"app-{2 - i}"]
            assert record["created_at"] is not None

    def test_invalid_cluster_name(self, plat_mgt_api_client):
        invalid_cluster_name = "invalid-cluster-name"
        url = reverse("plat_mgt.infras.cluster.retrieve_nodes_state", kwargs={"cluster_name": invalid_cluster_name})
        response = plat_mgt_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
