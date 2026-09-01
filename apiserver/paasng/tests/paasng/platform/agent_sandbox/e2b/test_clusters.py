# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from django.db import connections

from paas_wl.infras.cluster.constants import (
    ClusterAllocationPolicyCondType,
    ClusterAllocationPolicyType,
    ClusterUsage,
)
from paas_wl.infras.cluster.entities import AllocationPolicy, AllocationPrecedencePolicy
from paas_wl.infras.cluster.models import Cluster, ClusterAllocationPolicy, ClusterE2BConfig
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.agent_sandbox.e2b.clusters import get_e2b_cluster_config, select_e2b_cluster
from paasng.platform.agent_sandbox.e2b.exceptions import E2BClusterNotConfigured, E2BClusterUnavailable
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def e2b_config() -> ClusterE2BConfig:
    """给测试集群登记一份 e2b 配置。"""
    return ClusterE2BConfig.objects.create(
        cluster=Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING),
        control_plane_url="http://e2b-gateway.bcs-system:8080",
        data_plane_address="e2b.example.com",
        api_key="e2b_real_gateway_key",
        tenant_id=DEFAULT_TENANT_ID,
    )


@pytest.mark.usefixtures("e2b_config")
class TestSelectCluster:
    def test_returns_configured_cluster(self):
        assert select_e2b_cluster(DEFAULT_TENANT_ID).name == CLUSTER_NAME_FOR_TESTING

    def test_rejects_when_all_clusters_disabled(self, e2b_config):
        """所有集群都停用后必须选不出来，由调用方转成 503。"""
        e2b_config.enabled = False
        e2b_config.save(update_fields=["enabled"])

        with pytest.raises(E2BClusterUnavailable):
            select_e2b_cluster(DEFAULT_TENANT_ID)

    def test_rejects_when_no_policy_for_tenant(self):
        """租户没有分配策略时分配器抛 ValueError，这里要转成自己的异常。"""
        with pytest.raises(E2BClusterUnavailable):
            select_e2b_cluster("tenant-without-policy")


class TestSelectClusterWithoutConfig:
    def test_rejects_cluster_not_registered(self):
        """集群被策略选中但没登记 e2b 配置，同样不能用于 e2b 沙箱。"""
        with pytest.raises(E2BClusterUnavailable):
            select_e2b_cluster(DEFAULT_TENANT_ID)


class TestSelectClusterUsage:
    """验证分配用途固定为 agent_sandbox_isolated。

    做法是只给某个用途配规则：能选出集群就说明上下文里的 usage 是它，
    比断言构造参数更接近真实的调度行为。
    """

    @pytest.fixture()
    def apply_policy_for_usage(self, e2b_config):
        """把测试集群改成只服务于指定用途。"""

        def _apply(usage: ClusterUsage):
            policy = ClusterAllocationPolicy.objects.get(tenant_id=DEFAULT_TENANT_ID)
            policy.type = ClusterAllocationPolicyType.RULE_BASED
            policy.allocation_precedence_policies = [
                AllocationPrecedencePolicy(
                    matcher={ClusterAllocationPolicyCondType.USAGE_IS: usage.value},
                    policy=AllocationPolicy(env_specific=False, clusters=[CLUSTER_NAME_FOR_TESTING]),
                )
            ]
            policy.save()

        return _apply

    def test_matches_isolated_usage_rule(self, apply_policy_for_usage):
        apply_policy_for_usage(ClusterUsage.AGENT_SANDBOX_ISOLATED)

        assert select_e2b_cluster(DEFAULT_TENANT_ID).name == CLUSTER_NAME_FOR_TESTING


class TestGetClusterConfig:
    def test_returns_registered_config(self, e2b_config):
        config = get_e2b_cluster_config(CLUSTER_NAME_FOR_TESTING)

        assert config.pk == e2b_config.pk
        assert config.control_plane_url == "http://e2b-gateway.bcs-system:8080"
        # 凭证以密文入库，读回时透明解密
        assert config.api_key == "e2b_real_gateway_key"

    def test_rejects_disabled_config(self, e2b_config):
        e2b_config.enabled = False
        e2b_config.save(update_fields=["enabled"])

        with pytest.raises(E2BClusterNotConfigured):
            get_e2b_cluster_config(CLUSTER_NAME_FOR_TESTING)

    def test_rejects_unregistered_cluster(self):
        with pytest.raises(E2BClusterNotConfigured):
            get_e2b_cluster_config("cluster-never-registered")


def test_credentials_are_encrypted_at_rest(e2b_config):
    """验证凭证是否被加密落库"""
    with connections["workloads"].cursor() as cursor:
        cursor.execute(f"SELECT api_key FROM {ClusterE2BConfig._meta.db_table}")  # noqa: S608
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert e2b_config.api_key not in rows[0][0]
