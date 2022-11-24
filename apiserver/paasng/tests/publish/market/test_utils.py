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

from paasng.engine.constants import JobStatus
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.region.models import get_all_regions
from paasng.publish.entrance.exposer import SubDomainURLProvider, SubPathURLProvider
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.publish.market.models import AvailableAddress, MarketConfig
from paasng.publish.market.utils import MarketAvailableAddressHelper
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.mocks.domain import FakeCustomDomainService
from tests.utils.mocks.engine import replace_cluster_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    """Replace cluster info in module level"""
    with replace_cluster_service(
        ingress_config={
            'app_root_domains': [{'name': 'example.com', 'https_enabled': True}],
            'sub_path_domains': [{'name': 'example.com', 'https_enabled': True}],
        }
    ):
        yield


@pytest.fixture
def domain_svc():
    """Replace real custom domain service with fake one"""
    with mock.patch(
        'paasng.publish.market.utils.CustomDomainService', new_callable=FakeCustomDomainService
    ) as domain_svc:
        yield domain_svc


class TestMarketAvailableAddressHelper:
    @pytest.fixture(autouse=True)
    def make_deployment(self, bk_module):
        create_fake_deployment(bk_module, status=JobStatus.SUCCESSFUL.value)

    @pytest.mark.parametrize(
        'exposed_url_type, address_cls',
        [
            (ExposedURLType.SUBDOMAIN.value, SubDomainURLProvider),
            (ExposedURLType.SUBPATH.value, SubPathURLProvider),
        ],
    )
    def test_list_by_exposed_url_type(self, exposed_url_type, address_cls, bk_app, bk_module, domain_svc):
        for region in get_all_regions().keys():
            market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
            market_config.source_module.region = region
            market_config.source_module.exposed_url_type = exposed_url_type
            market_config.prefer_https = False
            market_config.source_module.save()

            helper = MarketAvailableAddressHelper(market_config)

            domain_svc.set_hostnames(['test.example.com'])
            default_entrance = address_cls(helper.env).provide()
            assert helper.addresses == [
                AvailableAddress(address=default_entrance.address.replace("https://", "http://"), type=2),
                AvailableAddress(address=default_entrance.address.replace("http://", "https://"), type=5),
                AvailableAddress(address="http://test.example.com", type=4),
            ]

    @pytest.mark.parametrize(
        'exposed_url_type, address_cls',
        [
            (ExposedURLType.SUBDOMAIN.value, SubDomainURLProvider),
            (ExposedURLType.SUBPATH.value, SubPathURLProvider),
        ],
    )
    def test_prefer_https(self, exposed_url_type, address_cls, bk_app, bk_module, domain_svc):
        for region in get_all_regions().keys():
            market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
            market_config.source_module.region = region
            market_config.source_module.exposed_url_type = exposed_url_type
            market_config.prefer_https = True
            market_config.source_module.save()

            helper = MarketAvailableAddressHelper(market_config)

            domain_svc.set_hostnames(['test.example.com'])
            default_entrance = address_cls(helper.env).provide()
            assert default_entrance.url.protocol == "https"
            assert helper.addresses == [
                AvailableAddress(address=default_entrance.address, type=2),
                AvailableAddress(address="http://test.example.com", type=4),
            ]

    @pytest.mark.parametrize(
        'exposed_url_type, address_cls',
        [
            (ExposedURLType.SUBDOMAIN.value, SubDomainURLProvider),
            (ExposedURLType.SUBPATH.value, SubPathURLProvider),
        ],
    )
    def test_https_unsupported(self, exposed_url_type, address_cls, bk_app, bk_module, domain_svc):
        with replace_cluster_service(
            ingress_config={
                'app_root_domains': [{'name': 'example.com', 'https_enabled': False}],
                'sub_path_domains': [{'name': 'example.com', 'https_enabled': False}],
            }
        ):
            for region in get_all_regions().keys():
                market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
                market_config.source_module.region = region
                market_config.source_module.exposed_url_type = exposed_url_type
                market_config.prefer_https = True
                market_config.source_module.save()

                helper = MarketAvailableAddressHelper(market_config)

                domain_svc.set_hostnames(['test.example.com'])
                default_entrance = address_cls(helper.env).provide()
                assert default_entrance.url.protocol == "http"
                assert helper.addresses == [
                    AvailableAddress(address=default_entrance.address, type=2),
                    AvailableAddress(address="http://test.example.com", type=4),
                ]

    @pytest.mark.parametrize(
        'filter_domain,results',
        [
            ('http://test.example.com', AvailableAddress(address="http://test.example.com", type=4)),
            ('http://404.bking.com', None),
        ],
    )
    def test_filter_domain_address_not_found(self, filter_domain, results, bk_app, bk_module, domain_svc):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.source_module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
        market_config.source_module.save()

        helper = MarketAvailableAddressHelper(market_config)

        domain_svc.set_hostnames(['test.example.com'])
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

    def test_access_entrance_for_custom_domain(self, bk_app, bk_module, domain_svc):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.source_url_type = ProductSourceUrlType.CUSTOM_DOMAIN.value
        market_config.custom_domain_url = "http://test.example.com"
        market_config.save()
        helper = MarketAvailableAddressHelper(market_config)

        domain_svc.set_hostnames(["test.example.com"])
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
    def test_list_without_deploy(self, bk_app, bk_module, domain_svc):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        helper = MarketAvailableAddressHelper(market_config)

        domain_svc.set_hostnames(['test.example.com'])

        assert helper.addresses == [
            AvailableAddress(address=None, type=2),
            AvailableAddress(address="http://test.example.com", type=4),
        ]
