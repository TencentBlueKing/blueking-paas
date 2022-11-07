# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
"""Testcases for application entrance management
"""
from contextlib import contextmanager
from unittest import mock

import pytest
from django.conf import settings

from paasng.engine.constants import JobStatus
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module
from paasng.publish.entrance.domains import ModuleEnvDomains
from paasng.publish.entrance.exposer import (
    LegacyEngineURLProvider,
    MarketURLProvider,
    get_exposed_url,
    get_module_exposed_links,
    update_exposed_url_type_to_subdomain,
)
from paasng.publish.market.constant import AppType
from paasng.publish.market.models import MarketConfig, Product
from paasng.publish.market.utils import MarketAvailableAddressHelper
from paasng.publish.sync_market.handlers import register_application_with_default
from paasng.publish.sync_market.managers import AppManger
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.helpers import initialize_module
from tests.utils.mocks.engine import replace_cluster_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    """Replace cluster info in module level"""
    with replace_cluster_service(
        ingress_config={
            'sub_path_domains': [{"name": 'sub.example.com'}, {"name": 'sub.example.cn'}],
            'app_root_domains': [{"name": 'bkapps.example.com'}],
        }
    ):
        yield


@pytest.fixture()
def bk_app(bk_app):
    bk_app.code = 'some-app-o'
    bk_app.name = "some-app-o"
    bk_app.save()
    return bk_app


class TestModuleEnvDomains:
    def test_prod_default(self, bk_app, bk_module):
        env = bk_module.envs.get(environment='prod')
        domains = ModuleEnvDomains(env).all()
        assert [d.host for d in domains] == [
            'prod-dot-default-dot-some-app-o.bkapps.example.com',
            'prod-dot-some-app-o.bkapps.example.com',
            'some-app-o.bkapps.example.com',
        ]

    def test_stag_default(self, bk_module):
        env = bk_module.envs.get(environment='stag')
        domains = ModuleEnvDomains(env).all()
        assert [d.host for d in domains] == [
            'stag-dot-default-dot-some-app-o.bkapps.example.com',
            'stag-dot-some-app-o.bkapps.example.com',
        ]

    def test_stag_non_default(self, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save()

        env = bk_stag_env
        domains = ModuleEnvDomains(env).all()
        assert [d.host for d in domains] == [
            'stag-dot-default-dot-some-app-o.bkapps.example.com',
        ]

    @pytest.mark.parametrize("https_enabled, expected_scheme", ((True, "https"), (False, "http")))
    def test_enable_https_by_default(self, https_enabled, expected_scheme, bk_stag_env):
        with replace_cluster_service(
            ingress_config={'app_root_domains': [{'name': 'example.com', 'https_enabled': https_enabled}]}
        ):
            domains = ModuleEnvDomains(bk_stag_env).all()
            assert domains[0].https_enabled == https_enabled
            assert domains[0].as_url().protocol == expected_scheme


class TestModuleEnvDomainsCodeWithUnderscore:
    @pytest.fixture()
    def bk_app(self, bk_app):
        bk_app.code = 'some_app'
        bk_app.save()
        return bk_app

    def test_prod_default(self, bk_app, bk_module):
        env = bk_module.envs.get(environment='prod')
        domains = ModuleEnvDomains(env).all()
        assert [d.host for d in domains] == [
            'prod-dot-default-dot-some--app.bkapps.example.com',
            'prod-dot-some--app.bkapps.example.com',
            'some--app.bkapps.example.com',
        ]


class TestMarketURLProvider:
    @pytest.fixture(autouse=True)
    def setUp(self, bk_module):
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)

    def test_env_without_market(self, bk_module, bk_prod_env):
        env = bk_module.envs.get(environment='prod')
        url = MarketURLProvider(env).provide()
        assert url is None

    def test_env_with_market(self, bk_app, bk_module, bk_stag_env, bk_prod_env):
        # Enable market
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.enabled = True
        market_config.save()

        url = MarketURLProvider(bk_prod_env).provide()
        assert url
        assert url.provider_type == 'market'

        url = MarketURLProvider(bk_stag_env).provide()
        assert url is None

    def test_env_with_market_nondefault_module(self, bk_app):
        # Enable market
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.enabled = True
        market_config.save()

        # Create another non-default module
        nondefault_module = Module.objects.create(
            application=bk_app,
            region=bk_app.region,
            owner=bk_app.owner,
            creator=bk_app.owner,
            is_default=False,
            name='foo-module',
            exposed_url_type=ExposedURLType.SUBDOMAIN,
        )
        initialize_module(nondefault_module)
        create_fake_deployment(nondefault_module, 'prod', status=JobStatus.SUCCESSFUL.value)

        url = MarketURLProvider(nondefault_module.envs.get(environment='prod')).provide()
        assert url is None


class TestLegacyURLProvider:
    @pytest.fixture(autouse=True)
    def setUp(self, bk_module):
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)

    def test_env_normal(self, bk_prod_env):
        url = LegacyEngineURLProvider(bk_prod_env).provide()
        assert url
        assert url.provider_type == 'legacy'


class TestIntegratedNotDeployed:
    def test_normal(self, bk_stag_env, bk_prod_env, bk_module):
        assert get_exposed_url(bk_stag_env) is None
        assert get_exposed_url(bk_prod_env) is None

        urls = get_module_exposed_links(bk_module)
        assert urls == {
            'stag': {'deployed': False, 'url': None},
            'prod': {'deployed': False, 'url': None},
        }


class TestIntegratedLegacy:
    @pytest.fixture(autouse=True)
    def setUp(self, bk_module):
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)
        # Set exposed url type to default
        bk_module.exposed_url_type = None
        bk_module.save()

    def test_prod_env_without_market(self, bk_stag_env):
        url = get_exposed_url(bk_stag_env)
        assert url
        assert url.provider_type == 'legacy'

    def test_prod_env_with_market(self, bk_app, bk_prod_env):
        # Enable market
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        market_config.enabled = True
        market_config.save()

        url = get_exposed_url(bk_prod_env)
        assert url
        assert url.provider_type == 'market'

    def test_subdomain_without_market(self, bk_module, bk_stag_env):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.save()

        url = get_exposed_url(bk_stag_env)
        assert url
        assert url.provider_type == 'default_subdomain'

        # Test get_module_exposed_links also
        urls = get_module_exposed_links(bk_module)
        assert urls == {
            'stag': {'deployed': True, 'url': 'http://stag-dot-some-app-o.bkapps.example.com'},
            'prod': {'deployed': True, 'url': 'http://some-app-o.bkapps.example.com'},
        }

    def test_stag_env_offlined(self, bk_module, bk_stag_env):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.save()

        # Simulate case when stag environment was offline
        bk_stag_env.is_offlined = True
        bk_stag_env.save(update_fields=['is_offlined'])

        urls = get_module_exposed_links(bk_module)
        assert urls == {
            'stag': {'deployed': False, 'url': None},
            'prod': {'deployed': True, 'url': 'http://some-app-o.bkapps.example.com'},
        }


class TestUpdateExposedURLType:
    @pytest.fixture(autouse=True)
    def setUp(self, bk_module):
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)

    def test_normal(self, bk_module):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH
        bk_module.save()
        with mock.patch('paasng.publish.entrance.exposer.EngineDeployClient') as mocked_client:
            update_exposed_url_type_to_subdomain(bk_module)

        assert bk_module.exposed_url_type == ExposedURLType.SUBDOMAIN
        assert mocked_client().update_domains.called

    def test_with_legacy_market(self, bk_app, bk_module):
        if (
            getattr(settings, "BK_CONSOLE_DBCONF", None) is None
            or getattr(settings, "PAAS_LEGACY_DBCONF", None) is None
        ):
            pytest.skip("未开启市场配置, 跳过该测试")

        # create product
        Product.objects.update_or_create(
            application=bk_app,
            defaults={
                "code": bk_app.code,
                "name": bk_app.name,
                "introduction": "foo",
                "description": "bar",
                "type": AppType.PAAS_APP.value,
            },
        )

        @contextmanager
        def ensure_app_in_market():
            session = console_db.get_scoped_session()
            app = AppManger(session).get(bk_app.code)
            if not app:
                app = register_application_with_default(region=bk_app.region, code=bk_app.code, name=bk_app.name)
            yield app

        with ensure_app_in_market():
            # 只有开启市场才会同步连接到桌面
            bk_app.market_config.enabled = True
            bk_app.market_config.save()

            bk_module.exposed_url_type = ExposedURLType.SUBPATH
            bk_module.save()
            with mock.patch('paasng.publish.entrance.exposer.EngineDeployClient') as mocked_client:
                update_exposed_url_type_to_subdomain(bk_module)

            assert bk_module.exposed_url_type == ExposedURLType.SUBDOMAIN
            assert mocked_client().update_domains.called
            session = console_db.get_scoped_session()
            app = AppManger(session).get(bk_app.code)
            # 判断是否已同步至市场
            entrance = MarketAvailableAddressHelper(bk_app.market_config).access_entrance
            assert entrance
            assert app.external_url == entrance.address
