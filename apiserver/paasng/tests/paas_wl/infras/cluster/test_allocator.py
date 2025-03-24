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
from paas_wl.infras.cluster.shim import Cluster, ClusterAllocator, EnvClusterService
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.modules.constants import ExposedURLType

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


class TestEnvClusterService:
    @pytest.fixture(autouse=True)
    def _setup(self):
        """setup clusters and wl_apps"""
        Cluster.objects.all().delete()
        G(
            Cluster,
            name="default",
            is_default=True,
            exposed_url_type=ExposedURLType.SUBDOMAIN.value,
        )
        G(Cluster, name="extra-1", is_default=False)

    def test_empty_cluster_field(self, bk_stag_env):
        wl_app = bk_stag_env.wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = ""
        latest_config.save()
        wl_app.refresh_from_db()
        assert EnvClusterService(bk_stag_env).get_cluster().name == "default"

    def test_valid_cluster_field(self, bk_stag_env):
        wl_app = bk_stag_env.wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = "extra-1"
        latest_config.save()
        wl_app.refresh_from_db()
        assert EnvClusterService(bk_stag_env).get_cluster().name == "extra-1"

    def test_invalid_cluster_field(self, bk_stag_env):
        wl_app = bk_stag_env.wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = "invalid"
        latest_config.save()
        wl_app.refresh_from_db()
        with pytest.raises(Cluster.DoesNotExist):
            EnvClusterService(bk_stag_env).get_cluster()


class TestClusterAllocator:
    @pytest.fixture(autouse=True)
    def _setup(self):
        Cluster.objects.all().delete()
        G(Cluster, name="default-sz1", is_default=True, tenant_id="default")
        G(Cluster, name="default-sz0", is_default=False, tenant_id="default")
        G(Cluster, name="tencent-gz0", is_default=True, tenant_id="tencent")
        G(Cluster, name="blueking-sh0", is_default=True, tenant_id="default")
        G(Cluster, name="blueking-sz0", is_default=False, tenant_id="default")

    @pytest.fixture
    def _uniform_policy(self):
        G(
            ClusterAllocationPolicy,
            type=ClusterAllocationPolicyType.UNIFORM,
            allocation_policy=AllocationPolicy(env_specific=False, clusters=["default-sz0"]),
            tenant_id="default",
        )

    @pytest.fixture
    def _rule_based_policy(self):
        G(
            ClusterAllocationPolicy,
            type=ClusterAllocationPolicyType.RULE_BASED,
            allocation_precedence_policies=[
                AllocationPrecedencePolicy(
                    matcher={ClusterAllocationPolicyCondType.USERNAME_IN: "zhangsan, lisi"},
                    policy=AllocationPolicy(env_specific=False, clusters=["default-sz0", "default-sz1"]),
                ),
                AllocationPrecedencePolicy(
                    matcher={ClusterAllocationPolicyCondType.REGION_IS: "default"},
                    policy=AllocationPolicy(
                        env_specific=True,
                        env_clusters={
                            AppEnvironment.STAGING: ["default-sz0"],
                            AppEnvironment.PRODUCTION: ["default-sz1"],
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
                    policy=AllocationPolicy(env_specific=False, clusters=["default-sz1"]),
                ),
            ],
            tenant_id="default",
        )

    def test_legacy_list(self):
        ctx = AllocationContext(tenant_id="default", region="default", environment=AppEnvironment.PRODUCTION)
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"default-sz1", "default-sz0"}

        ctx = AllocationContext(tenant_id="blueking", region="blueking", environment=AppEnvironment.STAGING)
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"blueking-sh0", "blueking-sz0"}

    @pytest.mark.usefixtures("_uniform_policy")
    def test_policy_base_uniform_list(self):
        ctx = AllocationContext(tenant_id="default", region="default", environment=AppEnvironment.PRODUCTION)
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"default-sz0"}

    @pytest.mark.usefixtures("_rule_based_policy")
    def test_policy_base_rule_based_list(self):
        ctx = AllocationContext(
            tenant_id="default", region="default", environment=AppEnvironment.PRODUCTION, username="zhangsan"
        )
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"default-sz1", "default-sz0"}

        ctx.username = "wangwu"
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"default-sz1"}

        ctx.environment = AppEnvironment.STAGING
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"default-sz0"}

        ctx.region = "blueking"
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"blueking-sz0"}

        ctx.environment = AppEnvironment.PRODUCTION
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"blueking-sz0", "blueking-sh0"}

        ctx.region = "tencent"
        assert {c.name for c in ClusterAllocator(ctx).list()} == {"default-sz1"}

    @pytest.mark.usefixtures("_rule_based_policy")
    def test_get_with_cluster_name(self):
        ctx = AllocationContext(tenant_id="default", region="default", environment=AppEnvironment.PRODUCTION)
        assert ClusterAllocator(ctx).get("default-sz1").name == "default-sz1"

        ctx.region = "blueking"
        assert ClusterAllocator(ctx).get("blueking-sh0").name == "blueking-sh0"

        with pytest.raises(ValueError, match="got no cluster"):
            ClusterAllocator(ctx).get("invalid")

    def test_get_default_legacy(self):
        ctx = AllocationContext(tenant_id="default", region="default", environment=AppEnvironment.STAGING)
        assert ClusterAllocator(ctx).get_default().name == "default-sz1"

        ctx.region = "tencent"
        assert ClusterAllocator(ctx).get_default().name == "tencent-gz0"

    @pytest.mark.usefixtures("_uniform_policy")
    def test_get_default_with_uniform_policy(self):
        ctx = AllocationContext(tenant_id="default", region="default", environment=AppEnvironment.STAGING)
        assert ClusterAllocator(ctx).get_default().name == "default-sz0"

    @pytest.mark.usefixtures("_rule_based_policy")
    def test_get_default_with_rule_based_policy(self):
        ctx = AllocationContext(tenant_id="default", region="default", environment=AppEnvironment.STAGING)
        assert ClusterAllocator(ctx).get_default().name == "default-sz0"

        ctx.region = "tencent"
        assert ClusterAllocator(ctx).get_default().name == "default-sz1"

        ctx.region = "blueking"
        ctx.environment = AppEnvironment.PRODUCTION
        assert ClusterAllocator(ctx).get_default().name == "blueking-sz0"

        ctx.username = "zhangsan"
        assert ClusterAllocator(ctx).get_default().name == "default-sz0"
