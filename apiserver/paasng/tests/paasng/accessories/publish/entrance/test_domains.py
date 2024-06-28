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

"""Testcases for application entrance management
"""
import cattr
import pytest

from paas_wl.infras.cluster.models import Domain as DomainCfg
from paas_wl.infras.cluster.models import IngressConfig, PortMap
from paas_wl.workloads.networking.entrance.allocator.domains import (
    DomainPriorityType,
    ModuleEnvDomains,
    SubDomainAllocator,
)
from paasng.accessories.publish.entrance.domains import get_preallocated_domain, get_preallocated_domains_by_env
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetPreallocatedDomain:
    def test_not_configured(self):
        # Only subpath was configured
        domain = get_preallocated_domain(
            "test-code",
            ingress_config=cattr.structure(
                {"sub_path_domains": [{"name": "sub.example.com"}, {"name": "sub.example.cn"}]}, IngressConfig
            ),
        )
        assert domain is None

    @pytest.mark.parametrize(
        ("https_enabled", "expected_address"),
        [
            (True, "https://test-code.example.com"),
            (False, "http://test-code.example.com"),
        ],
    )
    def test_enable_https(self, https_enabled, expected_address):
        domain = get_preallocated_domain(
            "test-code",
            ingress_config=cattr.structure(
                {
                    "app_root_domains": [
                        {"name": "example.com", "https_enabled": https_enabled},
                        {"name": "example.cn", "https_enabled": https_enabled},
                    ],
                },
                IngressConfig,
            ),
        )
        assert domain
        assert domain.prod.as_url().as_address() == expected_address

    def test_without_module_name(self):
        domain = get_preallocated_domain(
            "test-code", ingress_config=cattr.structure({"app_root_domains": [{"name": "example.com"}]}, IngressConfig)
        )
        assert domain
        assert domain.stag.as_url().as_address() == "http://stag-dot-test-code.example.com"
        assert domain.prod.as_url().as_address() == "http://test-code.example.com"

    def test_with_module_name(self):
        domain = get_preallocated_domain(
            "test-code",
            ingress_config=cattr.structure({"app_root_domains": [{"name": "example.com"}]}, IngressConfig),
            module_name="api",
        )
        assert domain
        assert domain.stag.as_url().as_address() == "http://stag-dot-api-dot-test-code.example.com"
        assert domain.prod.as_url().as_address() == "http://prod-dot-api-dot-test-code.example.com"


@pytest.fixture()
def bk_app(bk_app):
    bk_app.code = "some-app-o"
    bk_app.name = "some-app-o"
    bk_app.save()
    return bk_app


@pytest.fixture(autouse=True)
def _setup_cluster():
    """Replace cluster info in module level"""
    with cluster_ingress_config({"app_root_domains": [{"name": "bar-1.example.com"}]}):
        yield


class TestModuleEnvDomains:
    def test_prod_default(self, bk_prod_env, bk_module):
        domains = ModuleEnvDomains(bk_prod_env).all()
        assert [d.host for d in domains] == [
            "prod-dot-default-dot-some-app-o.bar-1.example.com",
            "prod-dot-some-app-o.bar-1.example.com",
            "some-app-o.bar-1.example.com",
        ]

    def test_stag_default(self, bk_stag_env):
        domains = ModuleEnvDomains(bk_stag_env).all()
        assert [d.host for d in domains] == [
            "stag-dot-default-dot-some-app-o.bar-1.example.com",
            "stag-dot-some-app-o.bar-1.example.com",
        ]

    def test_stag_non_default(self, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save()

        domains = ModuleEnvDomains(bk_stag_env).all()
        assert [d.host for d in domains] == [
            "stag-dot-default-dot-some-app-o.bar-1.example.com",
        ]

    @pytest.mark.parametrize(("https_enabled", "expected_scheme"), [(True, "https"), (False, "http")])
    def test_enable_https_by_default(self, https_enabled, expected_scheme, bk_stag_env):
        with cluster_ingress_config({"app_root_domains": [{"name": "example.com", "https_enabled": https_enabled}]}):
            domains = ModuleEnvDomains(bk_stag_env).all()
            assert domains[0].https_enabled == https_enabled
            assert domains[0].as_url().protocol == expected_scheme


class TestModuleEnvDomainsCodeWithUnderscore:
    @pytest.fixture()
    def bk_app(self, bk_app):
        bk_app.code = "some_app"
        bk_app.save()
        return bk_app

    def test_prod_default(self, bk_app, bk_module):
        env = bk_module.envs.get(environment="prod")
        domains = ModuleEnvDomains(env).all()
        assert [d.host for d in domains] == [
            "prod-dot-default-dot-some--app.bar-1.example.com",
            "prod-dot-some--app.bar-1.example.com",
            "some--app.bar-1.example.com",
        ]


class TestSubDomainAllocator:
    @pytest.fixture()
    def allocator(self) -> SubDomainAllocator:
        return SubDomainAllocator("some-app", PortMap())

    @pytest.fixture()
    def domain_cfg(self) -> DomainCfg:
        return DomainCfg(name="example.com", https_enabled=True)

    def test_list_available_universal(self, bk_app, allocator, domain_cfg):
        domains = allocator.list_available([domain_cfg], "m1", "stag", is_default=False)
        assert [d.host for d in domains] == ["stag-dot-m1-dot-some-app.example.com"]

    def test_list_available_default(self, bk_app, allocator, domain_cfg):
        domains = allocator.list_available([domain_cfg], "m1", "prod", is_default=True)
        assert [d.host for d in domains] == [
            "prod-dot-m1-dot-some-app.example.com",
            "prod-dot-some-app.example.com",
            "some-app.example.com",
        ]

    def test_get_highest_priority_universal(self, bk_app, allocator, domain_cfg):
        domain = allocator.get_highest_priority(domain_cfg, "m1", "stag", is_default=False)
        assert domain.host == "stag-dot-m1-dot-some-app.example.com"
        assert domain.type == DomainPriorityType.STABLE
        assert domain.https_enabled is True

    def test_get_highest_priority_default(self, bk_app, allocator, domain_cfg):
        domain = allocator.get_highest_priority(domain_cfg, "m1", "stag", is_default=True)
        assert domain.host == "stag-dot-some-app.example.com"
        assert domain.type == DomainPriorityType.WITHOUT_MODULE

    def test_get_highest_priority_default_prod(self, allocator, domain_cfg):
        domain = allocator.get_highest_priority(domain_cfg, "m1", "prod", is_default=True)
        assert domain.host == "some-app.example.com"
        assert domain.type == DomainPriorityType.ONLY_CODE


class TestGetPreallocatedDomainsByEnv:
    @pytest.fixture(autouse=True)
    def _setup_cluster(self):
        """Replace cluster info in module level"""
        with cluster_ingress_config(
            {
                "app_root_domains": [
                    {"name": "bar-1.example.com"},
                    {"name": "bar-2.example.org"},
                ],
            }
        ):
            yield

    def test_default_prod_env(self, bk_module, bk_prod_env):
        bk_module.is_default = True
        bk_module.save(update_fields=["is_default"])

        results = get_preallocated_domains_by_env(bk_prod_env)
        assert [d.host for d in results] == [
            "some-app-o.bar-1.example.com",
            "some-app-o.bar-2.example.org",
        ]

    def test_non_default(self, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save(update_fields=["is_default"])

        results = get_preallocated_domains_by_env(bk_stag_env)
        assert [d.host for d in results] == [
            "stag-dot-default-dot-some-app-o.bar-1.example.com",
            "stag-dot-default-dot-some-app-o.bar-2.example.org",
        ]
