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
from typing import List

import pytest
from django.urls import reverse
from rest_framework import status

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyCondType, ClusterAllocationPolicyType
from paas_wl.infras.cluster.entities import AllocationRule, ManualAllocationConfig
from paas_wl.infras.cluster.models import ClusterAllocationPolicy
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.platform.applications.constants import AppEnvironment
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

# TODO（多租户）补充租户管理员视角


class TestClusterAllocationPolicyViewSet:
    @pytest.fixture
    def init_policies(self, init_system_cluster, init_default_cluster) -> List[ClusterAllocationPolicy]:
        manual_policy = ClusterAllocationPolicy.objects.create(
            tenant_id=OP_TYPE_TENANT_ID,
            type=ClusterAllocationPolicyType.MANUAL,
            manual_allocation_config=ManualAllocationConfig(env_specific=False, clusters=[init_system_cluster.name]),
        )
        rule_policy = ClusterAllocationPolicy.objects.create(
            tenant_id=DEFAULT_TENANT_ID,
            type=ClusterAllocationPolicyType.RULE,
            allocation_rules=[
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
        return [manual_policy, rule_policy]

    def test_list(self, init_policies, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(reverse("plat_mgt.infras.cluster_allocation_policy.bulk"))
        assert resp.status_code == status.HTTP_200_OK

    def test_create_manual_allocation_policy(self, plat_mgt_api_client, init_default_cluster):
        data = {
            "tenant_id": DEFAULT_TENANT_ID,
            "type": ClusterAllocationPolicyType.MANUAL,
            "manual_allocation_config": {
                "env_specific": False,
                "clusters": [init_default_cluster.name],
            },
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster_allocation_policy.bulk"), data=data)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_allocation_rules_policy(self, plat_mgt_api_client, init_system_cluster, init_default_cluster):
        data = {
            "tenant_id": DEFAULT_TENANT_ID,
            "type": ClusterAllocationPolicyType.RULE,
            "allocation_rules": [
                {
                    "env_specific": False,
                    "matcher": {ClusterAllocationPolicyCondType.REGION_IS: "ieod"},
                    "clusters": [init_system_cluster.name],
                },
                {
                    "env_specific": True,
                    "env_clusters": {
                        AppEnvironment.STAGING: [init_default_cluster.name],
                        AppEnvironment.PRODUCTION: [init_default_cluster.name, init_system_cluster.name],
                    },
                },
            ],
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster_allocation_policy.bulk"), data=data)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_policy_without_available_tenant_id(self, plat_mgt_api_client, init_default_cluster):
        """租户 ID 不在指定集群的可用租户列表中"""
        data = {
            "tenant_id": generate_random_string(8),
            "type": ClusterAllocationPolicyType.MANUAL,
            "manual_allocation_config": {
                "env_specific": False,
                "clusters": [init_default_cluster.name],
            },
        }
        resp = plat_mgt_api_client.post(reverse("plat_mgt.infras.cluster_allocation_policy.bulk"), data=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert f"集群名 {init_default_cluster.name} 不存在或不可用" in resp.json()["detail"]

    def test_update_policy(self, init_policies, init_system_cluster, init_default_cluster, plat_mgt_api_client):
        data = {
            # 虽然指定要修改 tenant_id，但是不会生效的
            "tenant_id": OP_TYPE_TENANT_ID,
            "type": ClusterAllocationPolicyType.RULE,
            "allocation_rules": [
                {
                    "env_specific": True,
                    "env_clusters": {
                        AppEnvironment.STAGING: [init_system_cluster.name],
                        AppEnvironment.PRODUCTION: [init_system_cluster.name, init_default_cluster.name],
                    },
                }
            ],
        }

        policy = init_policies[1]
        url = reverse(
            "plat_mgt.infras.cluster_allocation_policy.detail",
            kwargs={"policy_id": policy.uuid},
        )
        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        policy.refresh_from_db()
        assert policy.tenant_id != OP_TYPE_TENANT_ID
        assert policy.type == ClusterAllocationPolicyType.RULE

    def test_update_policy_without_available_tenant_id(self, init_policies, init_default_cluster, plat_mgt_api_client):
        data = {
            "type": ClusterAllocationPolicyType.RULE,
            "allocation_rules": [
                {
                    "env_specific": False,
                    "clusters": [init_default_cluster.name],
                }
            ],
        }

        policy = init_policies[0]
        url = reverse(
            "plat_mgt.infras.cluster_allocation_policy.detail",
            kwargs={"policy_id": policy.uuid},
        )
        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert f"集群名 {init_default_cluster.name} 不存在或不可用" in resp.json()["detail"]