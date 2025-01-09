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

"""Testcases for application entrance management"""

import cattr
import pytest
from django.test.utils import override_settings

from paas_wl.infras.cluster.entities import Domain as DomainCfg
from paas_wl.infras.cluster.entities import IngressConfig, PortMap
from paas_wl.workloads.networking.entrance.allocator.subpaths import (
    ModuleEnvSubpaths,
    SubPathAllocator,
    SubpathPriorityType,
)
from paasng.accessories.publish.entrance.subpaths import (
    get_legacy_compatible_path,
    get_preallocated_path,
    get_preallocated_paths_by_env,
)
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestModuleEnvSubpaths:
    @pytest.fixture()
    def bk_app(self, bk_app):
        bk_app.code = "some-app-o"
        bk_app.save()
        return bk_app

    @pytest.fixture(autouse=True)
    def _setup_cluster(self):
        # Enable USE_LEGACY_SUB_PATH_PATTERN by default
        with cluster_ingress_config(
            {"sub_path_domains": [{"name": "sub.example.com"}, {"name": "sub.example.cn"}]}
        ), override_settings(USE_LEGACY_SUB_PATH_PATTERN=True):
            yield

    def test_prod_default(self, bk_module):
        env = bk_module.envs.get(environment="prod")
        subpaths = ModuleEnvSubpaths(env).all()
        legacy_path = get_legacy_compatible_path(env)
        assert [d.as_url().as_address() for d in subpaths] == [
            "http://sub.example.com/prod--default--some-app-o/",
            "http://sub.example.cn/prod--default--some-app-o/",
            f"http://sub.example.com{legacy_path}",
            f"http://sub.example.cn{legacy_path}",
            "http://sub.example.com/prod--some-app-o/",
            "http://sub.example.cn/prod--some-app-o/",
            "http://sub.example.com/some-app-o/",
            "http://sub.example.cn/some-app-o/",
        ]
        p = ModuleEnvSubpaths(env).get_shortest()
        assert p is not None
        assert p.as_url().as_address() == "http://sub.example.cn/some-app-o/"

    def test_stag_default(self, bk_module):
        env = bk_module.envs.get(environment="stag")
        subpaths = ModuleEnvSubpaths(env).all()
        legacy_path = get_legacy_compatible_path(env)
        assert [d.as_url().as_address() for d in subpaths] == [
            "http://sub.example.com/stag--default--some-app-o/",
            "http://sub.example.cn/stag--default--some-app-o/",
            f"http://sub.example.com{legacy_path}",
            f"http://sub.example.cn{legacy_path}",
            "http://sub.example.com/stag--some-app-o/",
            "http://sub.example.cn/stag--some-app-o/",
        ]

    def test_stag_non_default(self, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save()

        env = bk_stag_env
        subpaths = ModuleEnvSubpaths(env).all()
        legacy_path = get_legacy_compatible_path(env)
        assert [d.as_url().as_address() for d in subpaths] == [
            "http://sub.example.com/stag--default--some-app-o/",
            "http://sub.example.cn/stag--default--some-app-o/",
            f"http://sub.example.com{legacy_path}",
            f"http://sub.example.cn{legacy_path}",
        ]

    def test_disable_legacy_pattern(self, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save()
        with override_settings(USE_LEGACY_SUB_PATH_PATTERN=False):
            subpaths = ModuleEnvSubpaths(bk_stag_env).all()
            assert [d.as_url().as_address() for d in subpaths] == [
                "http://sub.example.com/stag--default--some-app-o/",
                "http://sub.example.cn/stag--default--some-app-o/",
            ]


class TestModuleEnvSubpathsNotConfigured:
    @pytest.fixture(autouse=True)
    def _setup_cluster(self):
        with cluster_ingress_config({"sub_path_domains": []}):
            yield

    def test_prod_default(self, bk_module):
        env = bk_module.envs.get(environment="prod")
        subpaths = ModuleEnvSubpaths(env).all()
        assert [d.as_url().as_address() for d in subpaths] == []


class TestGetPreallocatedPath:
    def test_no_module_name(self):
        subpath = get_preallocated_path(
            "test-code",
            ingress_config=cattr.structure(
                {"sub_path_domains": [{"name": "sub.example.com"}, {"name": "sub.example.cn"}]}, IngressConfig
            ),
        )
        assert subpath
        assert subpath.stag.as_url().as_address() == "http://sub.example.com/stag--test-code/"
        assert subpath.prod.as_url().as_address() == "http://sub.example.com/test-code/"

    def test_with_module_name(self):
        subpath = get_preallocated_path(
            "test-code",
            ingress_config=cattr.structure(
                {"sub_path_domains": [{"name": "sub.example.com"}, {"name": "sub.example.cn"}]}, IngressConfig
            ),
            module_name="api",
        )
        assert subpath
        assert subpath.stag.as_url().as_address() == "http://sub.example.com/stag--api--test-code/"
        assert subpath.prod.as_url().as_address() == "http://sub.example.com/prod--api--test-code/"

    def test_https(self):
        subpath = get_preallocated_path(
            "test-code",
            ingress_config=cattr.structure(
                {
                    "sub_path_domains": [
                        {"name": "sub.example.com", "https_enabled": True},
                        {"name": "sub.example.cn"},
                    ],
                },
                IngressConfig,
            ),
        )
        assert subpath
        assert subpath.stag.as_url().as_address() == "https://sub.example.com/stag--test-code/"
        assert subpath.prod.as_url().as_address() == "https://sub.example.com/test-code/"


def test_get_legacy_compatible_path(bk_stag_env):
    module = bk_stag_env.module
    assert get_legacy_compatible_path(bk_stag_env) == f"/{module.region}-{bk_stag_env.engine_app.name}/"


class TestSubPathAllocator:
    @pytest.fixture()
    def allocator(self) -> SubPathAllocator:
        return SubPathAllocator("some-app", PortMap())

    @pytest.fixture()
    def domain_cfg(self) -> DomainCfg:
        return DomainCfg(name="example.com", https_enabled=True)

    def test_list_available_universal(self, bk_app, allocator, domain_cfg):
        subpaths = allocator.list_available([domain_cfg], "m1", "stag", is_default=False)
        assert [p.subpath for p in subpaths] == ["/stag--m1--some-app/"]

    def test_list_available_default(self, bk_app, allocator, domain_cfg):
        subpaths = allocator.list_available([domain_cfg], "m1", "prod", is_default=True)
        assert [p.subpath for p in subpaths] == [
            "/prod--m1--some-app/",
            "/prod--some-app/",
            "/some-app/",
        ]

    def test_get_highest_priority_universal(self, bk_app, allocator, domain_cfg):
        p = allocator.get_highest_priority(domain_cfg, "m1", "stag", is_default=False)
        assert p.subpath == "/stag--m1--some-app/"
        assert p.type == SubpathPriorityType.STABLE
        assert p.https_enabled is True

    def test_get_highest_priority_default(self, bk_app, allocator, domain_cfg):
        p = allocator.get_highest_priority(domain_cfg, "m1", "stag", is_default=True)
        assert p.subpath == "/stag--some-app/"
        assert p.type == SubpathPriorityType.WITHOUT_MODULE

    def test_get_highest_priority_default_prod(self, allocator, domain_cfg):
        p = allocator.get_highest_priority(domain_cfg, "m1", "prod", is_default=True)
        assert p.subpath == "/some-app/"
        assert p.type == SubpathPriorityType.ONLY_CODE


class TestGetPreallocatedPathsByEnv:
    @pytest.fixture(autouse=True)
    def _setup_cluster(self):
        """Replace cluster info in module level"""
        with cluster_ingress_config(
            {
                "sub_path_domains": [
                    {"name": "sub.example.com"},
                    {"name": "sub.example.org"},
                ]
            }
        ):
            yield

    def test_default_prod_env(self, bk_app, bk_module, bk_prod_env):
        bk_module.is_default = True
        bk_module.save(update_fields=["is_default"])

        results = get_preallocated_paths_by_env(bk_prod_env)
        assert [(d.host, d.subpath) for d in results] == [
            ("sub.example.com", f"/{bk_app.code}/"),
            ("sub.example.org", f"/{bk_app.code}/"),
        ]

    def test_non_default(self, bk_app, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save(update_fields=["is_default"])

        results = get_preallocated_paths_by_env(bk_stag_env)
        assert [(d.host, d.subpath) for d in results] == [
            ("sub.example.com", f"/stag--default--{bk_app.code}/"),
            ("sub.example.org", f"/stag--default--{bk_app.code}/"),
        ]
