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
from unittest import mock

import pytest

from paas_wl.networking.entrance.constants import AddressType
from paasng.platform.modules.constants import ExposedURLType
from paasng.publish.entrance.exposer import (
    Address,
    env_is_deployed,
    get_addresses,
    get_exposed_url,
    list_custom_addresses,
    list_module_custom_addresses,
)
from tests.publish.utils import ModuleLiveAddrs
from tests.utils.helpers import override_region_configs

pytestmark = pytest.mark.django_db


class TestModuleLiveAddrs:
    module_addrs_data = [
        {"env": "prod", "is_running": False, "addresses": []},
        {
            "env": "stag",
            "is_running": True,
            "addresses": [
                # The addresses was given in random order in purpose
                {"type": "subpath", "url": "http://bar.example.com/bar-2/", "is_sys_reserved": True},
                {"type": "custom", "url": "http://custom.example.com/"},
                {"type": "subdomain", "url": "http://foo.example.com/"},
                {"type": "unknown", "url": "http://unknown.example.com/"},
                {"type": "subpath", "url": "http://bar.example.com/bar/"},
            ],
        },
    ]

    def test_get_is_running(self):
        addrs = ModuleLiveAddrs(self.module_addrs_data)
        assert addrs.get_is_running('stag') is True
        assert addrs.get_is_running('prod') is False
        assert addrs.get_is_running('invalid-env') is False

    def test_get_addresses(self):
        addrs = ModuleLiveAddrs(self.module_addrs_data)
        assert addrs.get_addresses('prod') == []
        assert addrs.get_addresses('invalid-env') == []

        stag_addrs = addrs.get_addresses('stag')
        assert len(stag_addrs) == 5
        assert [addr.type for addr in stag_addrs] == ['subpath', 'subpath', 'subdomain', 'custom', 'unknown']

    def test_get_addresses_with_type(self):
        addrs = ModuleLiveAddrs(self.module_addrs_data)
        assert addrs.get_addresses('stag', addr_type='subpath') == [
            Address(AddressType.SUBPATH, "http://bar.example.com/bar/"),
            Address(AddressType.SUBPATH, "http://bar.example.com/bar-2/", True),
        ]


class TestModuleLiveAddrsAllAddrs:
    module_addrs_data = [
        {
            "env": "prod",
            "is_running": True,
            "addresses": [
                {"type": "custom", "url": "http://prod-custom.example.com/"},
            ],
        },
        {
            "env": "stag",
            "is_running": True,
            "addresses": [
                {"type": "custom", "url": "http://custom.example.com/"},
                {"type": "subdomain", "url": "http://foo.example.com/"},
            ],
        },
    ]

    def test_get_all_addresses(self):
        addrs = ModuleLiveAddrs(self.module_addrs_data)
        all_addrs = addrs.get_all_addresses()
        assert len(all_addrs) == 3
        assert [addr.type for addr in all_addrs] == ['subdomain', 'custom', 'custom']

    def test_get_all_addresses_with_type(self):
        addrs = ModuleLiveAddrs(self.module_addrs_data)
        assert len(addrs.get_all_addresses(addr_type='custom')) == 2


@pytest.fixture
def setup_addrs(bk_app):
    """Set up common mock and configs for testing functions related with addresses"""

    def update_region_hook(config):
        config['basic_info']['link_engine_app'] = "http://example.com/{region}-legacy-path/"

    with override_region_configs(bk_app.region, update_region_hook), mock.patch(
        'paasng.publish.entrance.exposer.get_live_addresses'
    ) as mocker:
        mocker.return_value = ModuleLiveAddrs(
            [
                {"env": "prod", "is_running": False, "addresses": []},
                {
                    "env": "stag",
                    "is_running": True,
                    "addresses": [
                        {"type": "subdomain", "url": "http://default-foo.example.com/"},
                        {"type": "subdomain", "url": "http://foo.example.com/"},
                        {"type": "subdomain", "url": "http://default-foo.example.org/"},
                        {"type": "subpath", "url": "http://bar.example.com/bar/"},
                        {"type": "custom", "url": "http://custom.example.com/"},
                    ],
                },
            ]
        )
        yield


def test_env_is_deployed(bk_stag_env, bk_prod_env, setup_addrs):
    # See setup_addrs for details
    assert env_is_deployed(bk_stag_env) is True
    assert env_is_deployed(bk_prod_env) is False


class TestGetAddresses:
    @pytest.fixture(autouse=True)
    def _setup(self, setup_addrs):
        yield

    def test_not_running(self, bk_prod_env):
        addrs = get_addresses(bk_prod_env)
        assert addrs == []

    def test_subpath(self, bk_module, bk_stag_env):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH
        bk_module.save()

        addrs = get_addresses(bk_stag_env)
        assert len(addrs) == 1 and addrs[0].url == 'http://bar.example.com/bar/'

    def test_subdomain(self, bk_module, bk_stag_env):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.save()

        addrs = get_addresses(bk_stag_env)
        assert len(addrs) == 3 and addrs[0].url == 'http://foo.example.com/'

    def test_none(self, bk_app, bk_module, bk_stag_env):
        bk_module.exposed_url_type = None
        bk_module.save()

        addrs = get_addresses(bk_stag_env)
        assert len(addrs) == 1 and addrs[0].url == f'http://example.com/{bk_app.region}-legacy-path/'


class TestGetExposedUrl:
    @pytest.fixture(autouse=True)
    def _setup(self, setup_addrs):
        yield

    def test_not_running(self, bk_prod_env):
        assert get_exposed_url(bk_prod_env) is None

    @pytest.mark.parametrize(
        "preferred_root, expected",
        [
            (None, "http://foo.example.com/"),
            ("example.org", "http://default-foo.example.org/"),
            # An invalid preferred root domain should have no effect
            ("invalid-example.com", "http://foo.example.com/"),
        ],
    )
    def test_preferred_root(self, preferred_root, expected, bk_module, bk_stag_env):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.user_preferred_root_domain = preferred_root
        bk_module.save()

        url = get_exposed_url(bk_stag_env)
        assert url is not None
        assert url.provider_type == 'subdomain'
        assert url.address == expected


def test_list_custom_addresses(bk_stag_env, bk_prod_env, setup_addrs):
    assert list_custom_addresses(bk_prod_env) == []
    assert list_custom_addresses(bk_stag_env) == [
        Address(AddressType.CUSTOM, "http://custom.example.com/"),
    ]


def test_list_module_custom_addresses(bk_module, setup_addrs):
    assert list_module_custom_addresses(bk_module) == [
        Address(AddressType.CUSTOM, "http://custom.example.com/"),
    ]
