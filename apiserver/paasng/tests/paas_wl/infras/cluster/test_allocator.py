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
from django_dynamic_fixture import G

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyCondType, ClusterAllocationPolicyType
from paas_wl.infras.cluster.entities import AllocationContext, AllocationPolicy, AllocationPrecedencePolicy
from paas_wl.infras.cluster.models import ClusterAllocationPolicy
from paas_wl.infras.cluster.shim import Cluster, ClusterAllocator
from paasng.platform.applications.constants import AppEnvironment
from tests.utils.basic import generate_random_string

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


class TestClusterAllocator:
    @pytest.fixture
    def random_tenant_id(self) -> str:
        return generate_random_string(12)

    @pytest.fixture(autouse=True)
    def _setup(self, random_tenant_id):
        Cluster.objects.all().delete()
        G(Cluster, name="random-sz1", tenant_id=random_tenant_id)
        G(Cluster, name="random-sz0", tenant_id=random_tenant_id)
        G(Cluster, name="tencent-gz0", tenant_id="tencent")
        G(Cluster, name="blueking-sh0", tenant_id=random_tenant_id)
        G(Cluster, name="blueking-sz0", tenant_id=random_tenant_id)

    @pytest.fixture
    def _uniform_policy(self, random_tenant_id):
        G(
            ClusterAllocationPolicy,
            type=ClusterAllocationPolicyType.UNIFORM,
            allocation_policy=AllocationPolicy(env_specific=False, clusters=["random-sz0"]),
            tenant_id=random_tenant_id,
        )

    @pytest.fixture
    def _rule_based_policy(self, random_tenant_id):
        G(
            ClusterAllocationPolicy,
            type=ClusterAllocationPolicyType.RULE_BASED,
            allocation_precedence_policies=[
                AllocationPrecedencePolicy(
                    matcher={ClusterAllocationPolicyCondType.USERNAME_IN: "zhangsan, lisi"},
                    policy=AllocationPolicy(env_specific=False, clusters=["random-sz0", "random-sz1"]),
                ),
                AllocationPrecedencePolicy(
                    matcher={ClusterAllocationPolicyCondType.REGION_IS: "default"},
                    policy=AllocationPolicy(
                        env_specific=True,
                        env_clusters={
                            AppEnvironment.STAGING: ["random-sz0"],
                            AppEnvironment.PRODUCTION: ["random-sz1"],
                        },
                    ),
                ),
                AllocationPrecedencePolicy(
                    matcher={ClusterAllocationPolicyCondType.REGION_IS: "blueking"},
                    policy=AllocationPolicy(
                        env_specific=True,
                        env_clusters={
                            AppEnvironment.STAGING: ["blueking-sz0"],
                            AppEnvironment.PRODUCTION: ["blueking-sz0", "blueking-sh0"],
                        },
                    ),
                ),
                AllocationPrecedencePolicy(
                    matcher={},
                    policy=AllocationPolicy(env_specific=False, clusters=["random-sz1"]),
                ),
            ],
            tenant_id=random_tenant_id,
        )

    @pytest.mark.usefixtures("_uniform_policy")
    def test_policy_base_uniform_list(self, random_tenant_id):
        ctx = AllocationContext(tenant_id=random_tenant_id, region="default", environment=AppEnvironment.PRODUCTION)
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"random-sz0"}

    @pytest.mark.usefixtures("_rule_based_policy")
    def test_policy_base_rule_based_list(self, random_tenant_id):
        ctx = AllocationContext(
            tenant_id=random_tenant_id, region="default", environment=AppEnvironment.PRODUCTION, username="zhangsan"
        )
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"random-sz1", "random-sz0"}

        ctx.username = "wangwu"
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"random-sz1"}

        ctx.environment = AppEnvironment.STAGING
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"random-sz0"}

        ctx.region = "blueking"
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"blueking-sz0"}

        ctx.environment = AppEnvironment.PRODUCTION
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"blueking-sz0", "blueking-sh0"}

        ctx.region = "tencent"
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"random-sz1"}

    @pytest.mark.usefixtures("_rule_based_policy")
    def test_get_with_cluster_name(self, random_tenant_id):
        ctx = AllocationContext(tenant_id=random_tenant_id, region="default", environment=AppEnvironment.PRODUCTION)
        assert ClusterAllocator(ctx).get("random-sz1").name == "random-sz1"

        ctx.region = "blueking"
        assert ClusterAllocator(ctx).get("blueking-sh0").name == "blueking-sh0"

        with pytest.raises(ValueError, match="got no cluster"):
            ClusterAllocator(ctx).get("invalid")

    @pytest.mark.usefixtures("_uniform_policy")
    def test_get_default_with_uniform_policy(self, random_tenant_id):
        ctx = AllocationContext(tenant_id=random_tenant_id, region="default", environment=AppEnvironment.STAGING)
        assert ClusterAllocator(ctx).get_default().name == "random-sz0"

    @pytest.mark.usefixtures("_rule_based_policy")
    def test_get_default_with_rule_based_policy(self, random_tenant_id):
        ctx = AllocationContext(tenant_id=random_tenant_id, region="default", environment=AppEnvironment.STAGING)
        assert ClusterAllocator(ctx).get_default().name == "random-sz0"

        ctx.region = "tencent"
        assert ClusterAllocator(ctx).get_default().name == "random-sz1"

        ctx.region = "blueking"
        ctx.environment = AppEnvironment.PRODUCTION
        assert ClusterAllocator(ctx).get_default().name == "blueking-sz0"

        ctx.username = "zhangsan"
        assert ClusterAllocator(ctx).get_default().name == "random-sz0"
