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

"""Testcases entrance.exposer module"""

import json

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paas_wl.infras.cluster.entities import Domain, IngressConfig
from paas_wl.infras.cluster.models import Cluster
from paasng.accessories.publish.entrance.preallocated import (
    _ai_agent_market_address,
    _default_preallocated_urls,
    get_exposed_url_type,
    get_preallocated_address,
    get_preallocated_url,
    get_preallocated_urls,
)
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import ExposedURLType
from tests.paas_wl.utils.release import create_release
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetExposedUrlType:
    def test_non_existent(self):
        assert get_exposed_url_type("foo", "bar-module") is None

    def test_non_existent_module(self, bk_app):
        assert get_exposed_url_type(bk_app.code, "bar-module") is None

    def test_normal(self, bk_module):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH.value
        bk_module.save()
        assert get_exposed_url_type(bk_module.application.code, bk_module.name) == ExposedURLType.SUBPATH

        # Change the exposed URL type and test again
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
        bk_module.save()
        assert get_exposed_url_type(bk_module.application.code, bk_module.name) == ExposedURLType.SUBDOMAIN
        assert get_exposed_url_type(bk_module.application.code, None) == ExposedURLType.SUBDOMAIN, (
            "test default module"
        )


def test_default_preallocated_urls_empty(bk_stag_env):
    with cluster_ingress_config(replaced_config={}):
        urls = _default_preallocated_urls(bk_stag_env).kv_map["BKPAAS_DEFAULT_PREALLOCATED_URLS"]
        assert urls == ""


def test_default_preallocated_urls_normal(bk_stag_env):
    ingress_config = {"app_root_domains": [{"name": "example.com"}]}
    with cluster_ingress_config(replaced_config=ingress_config):
        urls = _default_preallocated_urls(bk_stag_env).kv_map["BKPAAS_DEFAULT_PREALLOCATED_URLS"]
        assert isinstance(urls, str)
        assert set(json.loads(urls).keys()) == {"stag", "prod"}


@pytest.mark.usefixtures("_with_wl_apps")
class TestAIAgentMarketAddress:
    """Test AI Agent market address env var injection."""

    def test_non_ai_agent_app_not_injected(self, bk_prod_env):
        """非 AI Agent 应用不注入."""
        bk_prod_env.application.is_ai_agent_app = False
        bk_prod_env.application.save()

        result = _ai_agent_market_address(bk_prod_env)
        assert len(result) == 0

    def test_injects_market_entrance_url(self, bk_app, bk_module, bk_prod_env, bk_prod_wl_app, bk_user):
        """AI Agent 应用注入正确的 market_address 值."""
        bk_app.is_ai_agent_app = True
        bk_app.save()

        # 设置 exposed_url_type 为子域名模式以确定 URL 格式
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.save()

        # 创建成功的发布使 prod 环境处于 running 状态
        create_release(bk_prod_wl_app, bk_user)

        ingress_config = {"app_root_domains": [{"name": "example.com"}]}
        with cluster_ingress_config(config=ingress_config):
            result = _ai_agent_market_address(bk_prod_env)

        assert len(result) == 1
        assert result[0].key == "BKPAAS_MARKET_ENTRANCE_URL"
        assert result[0].value == f"http://{bk_app.code}.example.com"


class TestGetPreallocatedAddress:
    @pytest.fixture(autouse=True)
    def _setup(self):
        G(Application, code="test-code", region=settings.DEFAULT_REGION_NAME)

    def test_not_configured(self):
        with cluster_ingress_config(replaced_config={}), pytest.raises(ValueError, match=r"^failed to get.*"):
            get_preallocated_address("test-code")

    @pytest.mark.parametrize(
        ("ingress_config", "expected_address"),
        [
            ({"app_root_domains": [{"name": "foo.com"}]}, "http://test-code.foo.com"),
            ({"sub_path_domains": [{"name": "foo.com"}]}, "http://foo.com/test-code/"),
            (
                {"sub_path_domains": [{"name": "foo.com"}], "app_root_domains": [{"name": "foo.com"}]},
                "http://foo.com/test-code/",
            ),
        ],
    )
    def test_normal(self, ingress_config, expected_address):
        with cluster_ingress_config(replaced_config=ingress_config):
            assert get_preallocated_address("test-code").prod == expected_address

    @pytest.mark.parametrize(
        ("preferred_url_type", "expected_address"),
        [
            (ExposedURLType.SUBDOMAIN, "http://test-code.foo.com"),
            (ExposedURLType.SUBPATH, "http://foo.com/test-code/"),
        ],
    )
    def test_preferred_url_type(self, preferred_url_type, expected_address):
        ingress_config = {"sub_path_domains": [{"name": "foo.com"}], "app_root_domains": [{"name": "foo.com"}]}
        with cluster_ingress_config(replaced_config=ingress_config):
            assert (
                get_preallocated_address("test-code", preferred_url_type=preferred_url_type).prod == expected_address
            )

    def test_nonexistent_app_code(self):
        """Test when the application code does not exist in the database yet."""
        with cluster_ingress_config(replaced_config={"app_root_domains": [{"name": "example.com"}]}):
            addrs = get_preallocated_address("nonexistent-code")
            assert addrs.stag == "http://stag-dot-nonexistent-code.example.com"
            assert addrs.prod == "http://nonexistent-code.example.com"

    @pytest.mark.parametrize(
        ("clusters", "stag_address", "prod_address"),
        [
            # 同集群的情况
            (
                {
                    AppEnvName.STAG: Cluster(
                        name="c1",
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name="c1.foo.com", reserved=False)]),
                    ),
                    AppEnvName.PROD: Cluster(
                        name="c1",
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name="c1.foo.com", reserved=False)]),
                    ),
                },
                "http://c1.foo.com/stag--test-code/",
                "http://c1.foo.com/test-code/",
            ),
            # 不同集群, 类型相同的情况
            (
                {
                    AppEnvName.STAG: Cluster(
                        name="c1",
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name="c1.foo.com", reserved=False)]),
                    ),
                    AppEnvName.PROD: Cluster(
                        name="c2",
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name="c2.foo.com", reserved=False)]),
                    ),
                },
                "http://c1.foo.com/stag--test-code/",
                "http://c2.foo.com/test-code/",
            ),
            # 不同集群, 类型不同的情况
            (
                {
                    AppEnvName.STAG: Cluster(
                        name="c1",
                        ingress_config=IngressConfig(
                            sub_path_domains=[Domain(name="c1.foo.com", reserved=False)],
                        ),
                    ),
                    AppEnvName.PROD: Cluster(
                        name="c2",
                        ingress_config=IngressConfig(
                            app_root_domains=[Domain(name="c2.foo.com", reserved=False)],
                        ),
                    ),
                },
                "http://c1.foo.com/stag--test-code/",
                "http://test-code.c2.foo.com",
            ),
            # 优先级的情况
            (
                {
                    AppEnvName.STAG: Cluster(
                        name="c1",
                        ingress_config=IngressConfig(app_root_domains=[Domain(name="c1.foo.com", reserved=False)]),
                    ),
                    AppEnvName.PROD: Cluster(
                        name="c2",
                        ingress_config=IngressConfig(
                            sub_path_domains=[Domain(name="c2.foo.com", reserved=False)],
                            app_root_domains=[Domain(name="c2.foo.com", reserved=False)],
                        ),
                    ),
                },
                "http://stag-dot-test-code.c1.foo.com",
                "http://c2.foo.com/test-code/",
            ),
        ],
    )
    def test_with_clusters(self, clusters, stag_address, prod_address):
        addr = get_preallocated_address("test-code", clusters=clusters)
        assert addr.prod == prod_address
        assert addr.stag == stag_address


class TestDefaultEntrance:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with cluster_ingress_config(
            config={
                "app_root_domains": [
                    {"name": "bar-1.example.com"},
                    {"name": "bar-2.example.org"},
                ],
            }
        ):
            yield

    def test_single_entrance(self, bk_app, bk_module, bk_stag_env):
        """Test: default module's stag env"""
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.is_default = True
        bk_module.save()

        url = get_preallocated_url(bk_stag_env)
        assert url is not None
        assert url.address == f"http://stag-dot-{bk_app.code}.bar-1.example.com"

    def test_sub_domain(self, bk_app, bk_module, bk_stag_env):
        """Test: default module's stag env"""
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.is_default = True
        bk_module.save()

        urls = get_preallocated_urls(bk_stag_env)
        assert [u.address for u in urls] == [
            f"http://stag-dot-{bk_app.code}.bar-1.example.com",
            f"http://stag-dot-{bk_app.code}.bar-2.example.org",
        ]
