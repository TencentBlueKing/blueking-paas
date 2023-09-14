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
"""Testcases for application entrance management
"""
from contextlib import contextmanager
from unittest import mock

import pytest
from django.conf import settings

from paas_wl.networking.entrance.addrs import Address, AddressType
from paasng.engine.constants import JobStatus
from paasng.platform.core.storages.sqlalchemy import console_db
from paasng.platform.modules.constants import ExposedURLType
from paasng.publish.entrance.exposer import (
    get_exposed_url,
    get_module_exposed_links,
    update_exposed_url_type_to_subdomain,
)
from paasng.publish.market.constant import AppType
from paasng.publish.market.models import Product
from paasng.publish.market.utils import MarketAvailableAddressHelper
from paasng.publish.sync_market.handlers import register_application_with_default
from paasng.publish.sync_market.managers import AppManger
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    """Replace cluster info in module level"""
    with mock_cluster_service(
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


class TestIntegratedNotDeployed:
    def test_normal(self, bk_stag_env, bk_prod_env, bk_module, mock_env_is_running, mock_get_builtin_addresses):
        assert get_exposed_url(bk_stag_env) is None
        assert get_exposed_url(bk_prod_env) is None

        urls = get_module_exposed_links(bk_module)
        assert urls == {
            'stag': {'deployed': False, 'url': None},
            'prod': {'deployed': False, 'url': None},
        }


def test_get_module_exposed_links(
    bk_module, bk_stag_env, bk_prod_env, mock_env_is_running, mock_get_builtin_addresses
):
    mock_env_is_running[bk_stag_env] = True
    mock_env_is_running[bk_prod_env] = True
    mock_get_builtin_addresses[bk_stag_env] = [Address(type=AddressType.SUBDOMAIN, url="http://foo-stag.example.com")]
    mock_get_builtin_addresses[bk_prod_env] = [Address(type=AddressType.SUBDOMAIN, url="http://foo-prod.example.com")]
    bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
    bk_module.save()

    urls = get_module_exposed_links(bk_module)
    assert urls == {
        'stag': {'deployed': True, 'url': 'http://foo-stag.example.com'},
        'prod': {'deployed': True, 'url': 'http://foo-prod.example.com'},
    }


@pytest.mark.django_db(databases=["default", "workloads"])
class TestUpdateExposedURLType:
    @pytest.fixture(autouse=True)
    def setUp(self, bk_module):
        create_fake_deployment(bk_module, 'stag', status=JobStatus.SUCCESSFUL.value)
        create_fake_deployment(bk_module, 'prod', status=JobStatus.SUCCESSFUL.value)

    def test_normal(self, bk_module):
        bk_module.exposed_url_type = ExposedURLType.SUBPATH
        bk_module.save()
        with mock.patch('paasng.publish.entrance.exposer.refresh_module_domains') as mocker:
            update_exposed_url_type_to_subdomain(bk_module)

        assert bk_module.exposed_url_type == ExposedURLType.SUBDOMAIN
        assert mocker.called

    def test_with_legacy_market(self, with_live_addrs, bk_app, bk_module):
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
            with mock.patch('paasng.publish.entrance.exposer.refresh_module_domains') as mocker:
                update_exposed_url_type_to_subdomain(bk_module)

            assert bk_module.exposed_url_type == ExposedURLType.SUBDOMAIN
            assert mocker.called
            session = console_db.get_scoped_session()
            app = AppManger(session).get(bk_app.code)

            # 判断是否已同步至市场
            entrance = MarketAvailableAddressHelper(bk_app.market_config).access_entrance
            assert entrance
            assert app.external_url == entrance.address
