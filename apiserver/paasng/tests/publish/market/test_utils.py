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
from unittest import mock

import pytest

from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.region.models import get_all_regions
from paasng.publish.entrance.exposer import Address, ModuleLiveAddrs
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.publish.market.models import AvailableAddress, MarketConfig
from paasng.publish.market.utils import MarketAvailableAddressHelper

pytestmark = pytest.mark.django_db


@pytest.fixture
def set_custom_domain():
    """Allow to set custom domains by mocking"""
    with mock.patch('paasng.publish.market.utils.list_custom_addresses') as mocker:

        def _set_hostname(hostname):
            """Set mocker to return given hostname as return value"""
            mocker.return_value = [Address(type='custom', url=f'http://{hostname}')]

        yield _set_hostname


class TestMarketAvailableAddressHelper:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with mock.patch('paasng.publish.entrance.exposer.get_live_addresses') as mocker:
            mocker.return_value = ModuleLiveAddrs(
                [
                    {
                        "env": "prod",
                        "is_running": True,
                        "addresses": [
                            {"type": "subdomain", "url": "https://foo.example.com"},
                            {"type": "subpath", "url": "https://example.org/foo/"},
                        ],
                    },
                ]
            )
            yield

    @pytest.mark.parametrize(
        'exposed_url_type, expected_addr',
        [
            (ExposedURLType.SUBDOMAIN.value, '//foo.example.com'),
            (ExposedURLType.SUBPATH.value, '//example.org/foo/'),
        ],
    )
    def test_no_prefer_different_exposed_type(self, exposed_url_type, expected_addr, bk_app, set_custom_domain):
        """No prefer HTTPS, test different exposed types"""
        for region in get_all_regions().keys():
            market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
            market_config.source_module.region = region
            market_config.source_module.exposed_url_type = exposed_url_type
            market_config.prefer_https = False
            market_config.source_module.save()

            set_custom_domain('test.example.com')
            helper = MarketAvailableAddressHelper(market_config)
            assert helper.addresses == [
                AvailableAddress(address='http:' + expected_addr, type=2),
                AvailableAddress(address='https:' + expected_addr, type=5),
                AvailableAddress(address="http://test.example.com", type=4),
            ]

    @pytest.mark.parametrize(
        'addr,expected_addr',
        [
            ('https://foo.example.com', 'https://foo.example.com'),
            ('http://foo.example.com', 'http://foo.example.com'),
        ],
    )
    def test_prefer_https(self, addr, expected_addr, bk_app, set_custom_domain):
        with mock.patch('paasng.publish.entrance.exposer.get_live_addresses') as mocker:
            mocker.return_value = ModuleLiveAddrs(
                [
                    {
                        "env": "prod",
                        "is_running": True,
                        "addresses": [{"type": "subdomain", "url": addr}],
                    },
                ]
            )

            for region in get_all_regions().keys():
                market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
                market_config.source_module.region = region
                market_config.source_module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
                market_config.prefer_https = True
                market_config.source_module.save()

                helper = MarketAvailableAddressHelper(market_config)

                set_custom_domain('test.example.com')
                assert helper.addresses == [
                    AvailableAddress(address=expected_addr, type=2),
                    AvailableAddress(address='http://test.example.com', type=4),
                ]

    @pytest.mark.parametrize(
        'filter_domain,results',
        [
            ('http://test.example.com', AvailableAddress(address="http://test.example.com", type=4)),
            ('http://404.bking.com', None),
        ],
    )
    def test_filter_domain_address_not_found(self, filter_domain, results, bk_app, bk_module, set_custom_domain):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.source_module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
        market_config.source_module.save()

        helper = MarketAvailableAddressHelper(market_config)

        set_custom_domain('test.example.com')
        assert helper.filter_domain_address(filter_domain) == results

    def test_access_entrance(self, bk_app):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.source_url_type = ProductSourceUrlType.ENGINE_PROD_ENV.value
        market_config.save()
        helper = MarketAvailableAddressHelper(market_config)

        assert helper.access_entrance
        assert helper.default_access_entrance_with_http
        assert helper.access_entrance.address == helper.default_access_entrance_with_http.address

        market_config.prefer_https = True
        market_config.save()
        assert helper.access_entrance.address == helper.default_access_entrance_with_https.address

    def test_access_entrance_for_custom_domain(self, bk_app, bk_module, set_custom_domain):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.source_url_type = ProductSourceUrlType.CUSTOM_DOMAIN.value
        market_config.custom_domain_url = "http://test.example.com"
        market_config.save()
        helper = MarketAvailableAddressHelper(market_config)

        set_custom_domain("test.example.com")
        entrance = helper.access_entrance
        assert entrance
        assert entrance.address == 'http://test.example.com'

    @pytest.mark.parametrize(
        'source_url_type,address',
        [
            (ProductSourceUrlType.THIRD_PARTY.value, "http://test.example.com"),
            (ProductSourceUrlType.DISABLED.value, None),
        ],
    )
    def test_different_access_entrance_url_type(self, source_url_type, address, bk_app, bk_module):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.source_url_type = source_url_type
        market_config.source_tp_url = "http://test.example.com"
        market_config.save()
        helper = MarketAvailableAddressHelper(market_config)

        entrance = helper.access_entrance
        if address is None:
            assert entrance is None
        else:
            assert entrance is not None
            assert entrance.address == address


class TestMarketAvailableAddressHelperNoDeployment:
    @mock.patch('paasng.publish.market.utils.get_exposed_url')
    def test_list_without_deploy(self, mocker, bk_app, bk_module, set_custom_domain):
        # Mock get_exposed_url to return None in order to simulate env which has
        # not been deployed yet.
        mocker.return_value = None

        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        helper = MarketAvailableAddressHelper(market_config)

        set_custom_domain('test.example.com')

        assert helper.addresses == [
            AvailableAddress(address=None, type=2),
            AvailableAddress(address="http://test.example.com", type=4),
        ]
