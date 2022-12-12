# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""Testcases entrance.exposer module
"""
import json
from unittest import mock

import pytest

from paasng.engine.constants import JobStatus
from paasng.engine.controller.models import Cluster, Domain, IngressConfig
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.publish.entrance.exposer import (
    ModuleLiveAddrs,
    SubDomainURLProvider,
    SubPathURLProvider,
    _default_preallocated_urls,
    get_exposed_url_live,
    get_module_exposed_links_live,
    get_preallocated_address,
)
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.mocks.engine import replace_cluster_service

pytestmark = pytest.mark.django_db


def test_default_preallocated_urls_empty(bk_stag_env):
    with replace_cluster_service(replaced_ingress_config={}):
        urls = _default_preallocated_urls(bk_stag_env)['BKPAAS_DEFAULT_PREALLOCATED_URLS']
        assert urls == ''


def test_default_preallocated_urls_normal(bk_stag_env):
    ingress_config = {'app_root_domains': [{"name": 'example.com'}]}
    with replace_cluster_service(replaced_ingress_config=ingress_config):
        urls = _default_preallocated_urls(bk_stag_env)['BKPAAS_DEFAULT_PREALLOCATED_URLS']
        assert isinstance(urls, str)
        assert set(json.loads(urls).keys()) == {'stag', 'prod'}


class TestGetPreallocatedAddress:
    def test_not_configured(self):
        with replace_cluster_service(replaced_ingress_config={}):
            with pytest.raises(ValueError):
                get_preallocated_address('test-code')

    @pytest.mark.parametrize(
        'ingress_config,expected_address',
        [
            ({'app_root_domains': [{"name": 'foo.com'}]}, 'http://test-code.foo.com'),
            ({'sub_path_domains': [{"name": 'foo.com'}]}, 'http://foo.com/test-code/'),
            (
                {'sub_path_domains': [{"name": 'foo.com'}], 'app_root_domains': [{"name": 'foo.com'}]},
                'http://foo.com/test-code/',
            ),
        ],
    )
    def test_normal(self, ingress_config, expected_address):
        with replace_cluster_service(replaced_ingress_config=ingress_config):
            assert get_preallocated_address('test-code').prod == expected_address

    @pytest.mark.parametrize(
        'clusters, stag_address, prod_address',
        [
            # 同集群的情况
            (
                {
                    AppEnvironment.STAGING.value: Cluster(
                        name='c1',
                        is_default=False,
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name='c1.foo.com', reserved=False)]),
                    ),
                    AppEnvironment.PRODUCTION.value: Cluster(
                        name='c1',
                        is_default=False,
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name='c1.foo.com', reserved=False)]),
                    ),
                },
                'http://c1.foo.com/stag--test-code/',
                'http://c1.foo.com/test-code/',
            ),
            # 不同集群, 类型相同的情况
            (
                {
                    AppEnvironment.STAGING.value: Cluster(
                        name='c1',
                        is_default=False,
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name='c1.foo.com', reserved=False)]),
                    ),
                    AppEnvironment.PRODUCTION.value: Cluster(
                        name='c2',
                        is_default=False,
                        ingress_config=IngressConfig(sub_path_domains=[Domain(name='c2.foo.com', reserved=False)]),
                    ),
                },
                'http://c1.foo.com/stag--test-code/',
                'http://c2.foo.com/test-code/',
            ),
            # 不同集群, 类型不同的情况
            (
                {
                    AppEnvironment.STAGING.value: Cluster(
                        name='c1',
                        is_default=False,
                        ingress_config=IngressConfig(
                            sub_path_domains=[Domain(name='c1.foo.com', reserved=False)],
                        ),
                    ),
                    AppEnvironment.PRODUCTION.value: Cluster(
                        name='c2',
                        is_default=False,
                        ingress_config=IngressConfig(
                            app_root_domains=[Domain(name='c2.foo.com', reserved=False)],
                        ),
                    ),
                },
                'http://c1.foo.com/stag--test-code/',
                'http://test-code.c2.foo.com',
            ),
            # 优先级的情况
            (
                {
                    AppEnvironment.STAGING.value: Cluster(
                        name='c1',
                        is_default=False,
                        ingress_config=IngressConfig(app_root_domains=[Domain(name='c1.foo.com', reserved=False)]),
                    ),
                    AppEnvironment.PRODUCTION.value: Cluster(
                        name='c2',
                        is_default=False,
                        ingress_config=IngressConfig(
                            sub_path_domains=[Domain(name='c2.foo.com', reserved=False)],
                            app_root_domains=[Domain(name='c2.foo.com', reserved=False)],
                        ),
                    ),
                },
                'http://stag-dot-test-code.c1.foo.com',
                'http://c2.foo.com/test-code/',
            ),
        ],
    )
    def test_with_clusters(self, clusters, stag_address, prod_address):
        addr = get_preallocated_address('test-code', clusters=clusters)
        assert addr.prod == prod_address
        assert addr.stag == stag_address


class TestSubPathURLProvider:
    @pytest.fixture(autouse=True)
    def _setup_deployment(self, bk_module):
        # Create a successful deployment or no address will be generated
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)
        with replace_cluster_service(
            replaced_ingress_config={'sub_path_domains': [{"name": 'foo.com'}, {"name": 'bar.com'}]}
        ):
            yield

    def test_disabled(self, bk_module, bk_prod_env):
        bk_module.exposed_url_type = None
        bk_module.save()

        url = SubPathURLProvider(bk_prod_env).provide()
        assert url is None

    @pytest.mark.parametrize(
        "bk_env, user_preferred_root_domain, expected_template",
        [
            ("bk_stag_env", None, "http://foo.com/stag--{bk_app.code}/"),
            ("bk_prod_env", None, "http://foo.com/{bk_app.code}/"),
            ("bk_stag_env", "bar.com", "http://bar.com/stag--{bk_app.code}/"),
            ("bk_prod_env", "bar.com", "http://bar.com/{bk_app.code}/"),
            ("bk_stag_env", "baz.com", "http://baz.com/stag--{bk_app.code}/"),
            ("bk_prod_env", "baz.com", "http://baz.com/{bk_app.code}/"),
        ],
        indirect=["bk_env"],
    )
    def test_enabled(self, bk_app, bk_module, bk_env, user_preferred_root_domain, expected_template):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH
        bk_module.user_preferred_root_domain = user_preferred_root_domain
        bk_module.save()

        url = SubPathURLProvider(bk_env).provide()
        assert url
        assert url.provider_type == 'subpath'
        assert url.address == expected_template.format(bk_app=bk_app)

    @pytest.mark.parametrize(
        "bk_env, user_preferred_root_domain, expected_templates",
        [
            (
                "bk_stag_env",
                None,
                ["http://foo.com/stag--{bk_app.code}/", "http://bar.com/stag--{bk_app.code}/"],
            ),
            ("bk_prod_env", None, ["http://foo.com/{bk_app.code}/", "http://bar.com/{bk_app.code}/"]),
            (
                "bk_stag_env",
                "bar.com",
                ["http://foo.com/stag--{bk_app.code}/", "http://bar.com/stag--{bk_app.code}/"],
            ),
            ("bk_prod_env", "bar.com", ["http://foo.com/{bk_app.code}/", "http://bar.com/{bk_app.code}/"]),
        ],
        indirect=["bk_env"],
    )
    def test_provide_all(self, bk_app, bk_module, bk_env, user_preferred_root_domain, expected_templates):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH
        bk_module.user_preferred_root_domain = user_preferred_root_domain
        bk_module.save()

        urls = SubPathURLProvider(bk_env).provide_all()
        assert urls is not None
        for url, expected_template in zip(urls, expected_templates):
            assert url.address == expected_template.format(bk_app=bk_app)

    def test_order_reserved(self, bk_app, bk_module, bk_prod_env):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH
        bk_module.save()
        with replace_cluster_service(
            replaced_ingress_config={'sub_path_domains': [{"name": 'foo.com', 'reserved': True}, {"name": 'fool.com'}]}
        ):
            url = SubPathURLProvider(bk_prod_env).provide()
            assert url
            assert url.address == "http://fool.com/{bk_app.code}/".format(bk_app=bk_app)


class TestSubDomainURLProvider:
    @pytest.fixture(autouse=True)
    def _setup_deployment(self, bk_module):
        # Create a successful deployment or no address will be generated
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)
        with replace_cluster_service(
            replaced_ingress_config={'app_root_domains': [{"name": 'foo.com'}, {"name": 'bar.com'}]}
        ):
            yield

    def test_disabled(self, bk_module, bk_prod_env):
        bk_module.exposed_url_type = None
        bk_module.save()

        url = SubDomainURLProvider(bk_prod_env).provide()
        assert url is None

    @pytest.mark.parametrize(
        "bk_env, user_preferred_root_domain, expected_template",
        [
            ("bk_stag_env", None, "http://stag-dot-{bk_app.code}.foo.com"),
            ("bk_prod_env", None, "http://{bk_app.code}.foo.com"),
            ("bk_stag_env", "bar.com", "http://stag-dot-{bk_app.code}.bar.com"),
            ("bk_prod_env", "bar.com", "http://{bk_app.code}.bar.com"),
            ("bk_stag_env", "baz.com", "http://stag-dot-{bk_app.code}.baz.com"),
            ("bk_prod_env", "baz.com", "http://{bk_app.code}.baz.com"),
        ],
        indirect=["bk_env"],
    )
    def test_enabled(self, bk_app, bk_module, bk_env, user_preferred_root_domain, expected_template):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.user_preferred_root_domain = user_preferred_root_domain
        bk_module.save()

        url = SubDomainURLProvider(bk_env).provide()
        assert url
        assert url.provider_type == 'default_subdomain'
        assert url.address == expected_template.format(bk_app=bk_app)

    @pytest.mark.parametrize(
        "bk_env, user_preferred_root_domain, expected_templates",
        [
            (
                "bk_stag_env",
                None,
                ["http://stag-dot-{bk_app.code}.foo.com", "http://stag-dot-{bk_app.code}.bar.com"],
            ),
            ("bk_prod_env", None, ["http://{bk_app.code}.foo.com", "http://{bk_app.code}.bar.com"]),
            (
                "bk_stag_env",
                "bar.com",
                ["http://stag-dot-{bk_app.code}.foo.com", "http://stag-dot-{bk_app.code}.bar.com"],
            ),
            ("bk_prod_env", "bar.com", ["http://{bk_app.code}.foo.com", "http://{bk_app.code}.bar.com"]),
        ],
        indirect=["bk_env"],
    )
    def test_provide_all(self, bk_app, bk_module, bk_env, user_preferred_root_domain, expected_templates):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.user_preferred_root_domain = user_preferred_root_domain
        bk_module.save()

        urls = SubDomainURLProvider(bk_env).provide_all()
        assert urls is not None
        for url, expected_template in zip(urls, expected_templates):
            assert url.address == expected_template.format(bk_app=bk_app)

    def test_order_reserved(self, bk_app, bk_module, bk_prod_env):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.save()
        with replace_cluster_service(
            replaced_ingress_config={'app_root_domains': [{"name": 'foo.com', 'reserved': True}, {"name": 'fool.com'}]}
        ):
            url = SubDomainURLProvider(bk_prod_env).provide()
            assert url
            assert url.address == "http://{bk_app.code}.fool.com".format(bk_app=bk_app)


@pytest.fixture
def module_addrs_data():
    return [
        {"env": "prod", "is_running": False, "addresses": []},
        {
            "env": "stag",
            "is_running": True,
            "addresses": [
                {"type": "subdomain", "url": "http://foo.example.com/"},
                {"type": "subpath", "url": "https://bar.example.com/bar/"},
            ],
        },
    ]


class TestModuleLiveAddrs:
    def test_get_is_running(self, module_addrs_data):
        addrs = ModuleLiveAddrs(module_addrs_data)
        assert addrs.get_is_running('stag') is True
        assert addrs.get_is_running('prod') is False
        assert addrs.get_is_running('invalid-env') is False

    def test_get_addresses(self, module_addrs_data):
        addrs = ModuleLiveAddrs(module_addrs_data)
        assert len(addrs.get_addresses('stag')) == 2
        assert addrs.get_addresses('prod') == []
        assert addrs.get_addresses('invalid-env') == []


@mock.patch('paasng.publish.entrance.exposer.get_live_addresses')
def test_get_module_exposed_links_live(mocker, module_addrs_data, bk_module):
    mocker.return_value = ModuleLiveAddrs(module_addrs_data)
    ret = get_module_exposed_links_live(bk_module)
    assert ret['stag'] == {'deployed': True, 'url': 'http://foo.example.com/'}


@mock.patch('paasng.publish.entrance.exposer.get_live_addresses')
def test_get_exposed_url_live(mocker, module_addrs_data, bk_stag_env, bk_prod_env):
    mocker.return_value = ModuleLiveAddrs(module_addrs_data)
    assert get_exposed_url_live(bk_stag_env) is not None
    assert get_exposed_url_live(bk_prod_env) is None
