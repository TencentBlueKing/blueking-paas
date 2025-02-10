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

import pytest
from django.conf import settings

from paas_wl.infras.cluster.constants import ClusterComponentName, ClusterFeatureFlag
from paas_wl.infras.cluster.entities import Domain, IngressConfig
from paas_wl.infras.cluster.models import APIServer, Cluster, ClusterComponent, ClusterElasticSearchConfig
from paas_wl.infras.resources.base.base import invalidate_global_configuration_pool
from paas_wl.workloads.networking.egress.cluster_state import get_digest_of_nodes_name
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from tests.utils.basic import generate_random_string


@pytest.fixture
def init_default_cluster() -> Cluster:
    """默认租户集群（即使是多租户，一般也不共享）"""
    cluster = Cluster.objects.create(
        region=settings.DEFAULT_REGION_NAME,
        tenant_id=DEFAULT_TENANT_ID,
        name=f"cluster-default-{generate_random_string(8)}",
        description="default tenant cluster",
        ingress_config=IngressConfig(
            sub_path_domains=[
                Domain(
                    name="bkapps.example.com",
                    reserved=False,
                    https_enabled=False,
                )
            ],
            frontend_ingress_ip="127.0.0.1",
        ),
        annotations={
            "bcs_project_id": "8470abd6fe455ca",
            "bcs_cluster_id": "BCS-K8S-00000",
            "bk_biz_id": "12345",
        },
        token_value="masked",
        feature_flags={
            ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: True,
            ClusterFeatureFlag.INGRESS_USE_REGEX: False,
            ClusterFeatureFlag.ENABLE_BK_MONITOR: True,
            ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR: True,
            ClusterFeatureFlag.ENABLE_AUTOSCALING: True,
            ClusterFeatureFlag.ENABLE_BCS_EGRESS: True,
        },
        available_tenant_ids=[DEFAULT_TENANT_ID],
    )
    # ApiServers
    APIServer.objects.create(
        cluster=cluster,
        host="http://bcs-api.example.com/clusters/BCS-K8S-00000",
        tenant_id=cluster.tenant_id,
    )
    # ES 配置
    ClusterElasticSearchConfig.objects.create(
        cluster=cluster,
        scheme="https",
        host="127.0.0.11",
        port=9200,
        username="admin",
        password="admin",
        tenant_id=cluster.tenant_id,
    )
    # 节点信息
    nodes_name = ["127.0.0.1", "127.0.0.2", "127.0.0.3"]
    nodes_digest = get_digest_of_nodes_name(nodes_name)
    RegionClusterState.objects.create(
        cluster_name=cluster.name,
        name=f"eng-cstate-{nodes_digest[:8]}-1",
        nodes_digest=nodes_digest,
        nodes_name=nodes_name,
        tenant_id=cluster.tenant_id,
    )
    # 集群组件
    components = [
        ClusterComponent(
            cluster=cluster,
            name=comp_name,
            required=bool(comp_name != ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER),
        )
        for comp_name in ClusterComponentName.get_values()
    ]
    ClusterComponent.objects.bulk_create(components)
    # 新添加集群后，需要刷新配置池
    invalidate_global_configuration_pool()

    return cluster


@pytest.fixture
def init_system_cluster() -> Cluster:
    """多租户模式下的运营租户集群（可多租户共享）"""
    cluster = Cluster.objects.create(
        region=settings.DEFAULT_REGION_NAME,
        tenant_id=OP_TYPE_TENANT_ID,
        name=f"cluster-system-{generate_random_string(8)}",
        description="op tenant cluster",
        ingress_config=IngressConfig(
            app_root_domains=[
                Domain(
                    name="bkapps.example.com",
                    reserved=False,
                    https_enabled=False,
                )
            ],
            frontend_ingress_ip="127.0.0.1",
        ),
        ca_data="MTIzNDU2Cg==",
        cert_data="MTIzNDU2Cg==",
        key_data="MTIzNDU2Cg==",
        feature_flags={
            ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: True,
            ClusterFeatureFlag.INGRESS_USE_REGEX: False,
            ClusterFeatureFlag.ENABLE_BK_MONITOR: True,
            ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR: True,
            ClusterFeatureFlag.ENABLE_AUTOSCALING: False,
            ClusterFeatureFlag.ENABLE_BCS_EGRESS: False,
        },
        available_tenant_ids=[OP_TYPE_TENANT_ID, DEFAULT_TENANT_ID],
    )
    # ApiServers
    APIServer.objects.bulk_create(
        [
            APIServer(cluster=cluster, host="http://127.0.0.8:6553", tenant_id=cluster.tenant_id),
            APIServer(cluster=cluster, host="http://127.0.0.9:6553", tenant_id=cluster.tenant_id),
        ]
    )
    # ES 配置
    ClusterElasticSearchConfig.objects.create(
        cluster=cluster,
        scheme="https",
        host="127.0.0.12",
        port=9200,
        username="blueking",
        password="blueking",
        tenant_id=cluster.tenant_id,
    )
    # 节点信息
    nodes_name = ["127.0.0.8", "127.0.0.9"]
    nodes_digest = get_digest_of_nodes_name(nodes_name)
    RegionClusterState.objects.create(
        cluster_name=cluster.name,
        name=f"eng-cstate-{nodes_digest[:8]}-1",
        nodes_digest=nodes_digest,
        nodes_name=nodes_name,
        tenant_id=cluster.tenant_id,
    )
    # 集群组件
    components = [
        ClusterComponent(
            cluster=cluster,
            name=comp_name,
            required=bool(comp_name != ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER),
        )
        for comp_name in ClusterComponentName.get_values()
    ]
    ClusterComponent.objects.bulk_create(components)
    # 新添加集群后，需要刷新配置池
    invalidate_global_configuration_pool()

    return cluster
