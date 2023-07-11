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
import pytest

from paas_wl.networking.ingress.models import Domain
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.publish.market.models import MarketConfig
from tests.conftest import CLUSTER_NAME_FOR_TESTING
from tests.paas_wl.utils.release import create_release
from tests.utils.helpers import (
    create_pending_wl_apps,
    generate_random_string,
    initialize_module,
    override_region_configs,
)

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


def create_module(bk_app):
    module = Module.objects.create(region=bk_app.region, application=bk_app, name=generate_random_string(length=8))
    initialize_module(module)
    return module


def set_subpath_exposed_url_type(region_config):
    region_config["entrance_config"]["exposed_url_type"] = ExposedURLType.SUBPATH


def set_subdomain_exposed_url_type(region_config):
    region_config["entrance_config"]["exposed_url_type"] = ExposedURLType.SUBDOMAIN


class TestAppEntranceViewSet:
    def test_list_all_entrances(self, bk_user, api_client, bk_app, bk_module, bk_stag_env, bk_stag_wl_app):
        url = f"/api/bkapps/applications/{bk_app.code}/entrances/"
        resp = api_client.get(url)
        # 未部署, 仅独立域名
        assert resp.json() == [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    'stag': [
                        {
                            'module': 'default',
                            'env': 'stag',
                            'address': {
                                'id': None,
                                'url': f'http://stag-dot-{bk_app.code}.example.com',
                                'type': 'subdomain',
                            },
                            'is_running': False,
                        }
                    ],
                    'prod': [
                        {
                            'module': 'default',
                            'env': 'prod',
                            'address': {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
                            'is_running': False,
                        }
                    ],
                },
            }
        ]

        # 添加独立域名
        # source type: custom
        custom_domain = Domain.objects.create(
            name='foo-custom.example.com',
            path_prefix='/subpath/',
            module_id=bk_module.id,
            environment_id=bk_stag_env.id,
        )

        resp = api_client.get(url)
        assert resp.json() == [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    'stag': [
                        {
                            'module': 'default',
                            'env': 'stag',
                            'address': {
                                'id': None,
                                'url': f'http://stag-dot-{bk_app.code}.example.com',
                                'type': 'subdomain',
                            },
                            'is_running': False,
                        },
                        {
                            'module': 'default',
                            'env': 'stag',
                            'address': {
                                'id': custom_domain.id,
                                'url': 'http://foo-custom.example.com/subpath/',
                                'type': 'custom',
                            },
                            'is_running': False,
                        },
                    ],
                    'prod': [
                        {
                            'module': 'default',
                            'env': 'prod',
                            'address': {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
                            'is_running': False,
                        }
                    ],
                },
            }
        ]

        # test field `is_running`
        create_release(bk_stag_env.wl_app, bk_user, failed=False)
        resp = api_client.get(url)
        assert resp.json() == [
            {
                "name": "default",
                "is_default": True,
                "envs": {
                    'stag': [
                        {
                            'module': 'default',
                            'env': 'stag',
                            'address': {
                                'id': None,
                                'url': f'http://stag-dot-{bk_app.code}.example.com',
                                'type': 'subdomain',
                            },
                            'is_running': True,
                        },
                        {
                            'module': 'default',
                            'env': 'stag',
                            'address': {
                                'id': custom_domain.id,
                                'url': 'http://foo-custom.example.com/subpath/',
                                'type': 'custom',
                            },
                            'is_running': True,
                        },
                    ],
                    'prod': [
                        {
                            'module': 'default',
                            'env': 'prod',
                            'address': {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
                            'is_running': False,
                        }
                    ],
                },
            }
        ]

    def test_list_module_all_entrances(self, api_client, bk_user, bk_app, bk_module, bk_prod_env, bk_prod_wl_app):
        # setup data
        # source type: custom
        Domain.objects.create(
            name='foo-custom.example.com',
            path_prefix='/subpath/',
            module_id=bk_module.id,
            environment_id=bk_prod_env.id,
        )

        with override_region_configs(bk_app.region, set_subpath_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/entrances/"
            resp = api_client.get(url)
            assert resp.json() == [
                {'id': None, 'url': f'http://example.com/{bk_app.code}/', 'type': 'subpath'},
                {
                    'id': Domain.objects.get(environment_id=bk_prod_env.id).id,
                    'url': 'http://foo-custom.example.com/subpath/',
                    'type': 'custom',
                },
            ]

        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/entrances/"
            resp = api_client.get(url)
            assert resp.json() == [
                {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
                {
                    'id': Domain.objects.get(environment_id=bk_prod_env.id).id,
                    'url': 'http://foo-custom.example.com/subpath/',
                    'type': 'custom',
                },
            ]

        another_m = create_module(bk_app)
        create_pending_wl_apps(bk_app, cluster_name=CLUSTER_NAME_FOR_TESTING)
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/modules/{another_m.name}/entrances/"
            resp = api_client.get(url)
            assert resp.json() == [
                {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
            ]

        another_prod_env = another_m.get_envs("prod")
        # source type: custom
        Domain.objects.create(
            name='foo-another.example.com',
            path_prefix='/subpath/',
            module_id=another_m.id,
            environment_id=another_prod_env.id,
        )
        with override_region_configs(bk_app.region, set_subpath_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/modules/{another_m.name}/entrances/"
            resp = api_client.get(url)
            assert resp.json() == [
                {'id': None, 'url': f'http://example.com/{bk_app.code}/', 'type': 'subpath'},
                {
                    'id': Domain.objects.get(environment_id=another_prod_env.id).id,
                    'url': 'http://foo-another.example.com/subpath/',
                    'type': 'custom',
                },
            ]

    def test_set_default_entrance(self, api_client, bk_user, bk_app, bk_module, bk_prod_env, bk_prod_wl_app):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        # setup data
        # source type: custom
        Domain.objects.create(
            name='foo-custom.example.com',
            path_prefix='/subpath/',
            module_id=bk_module.id,
            environment_id=bk_prod_env.id,
        )
        # 切换默认访问入口
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/entrances/default/"
            resp = api_client.post(
                url,
                data={
                    "module": bk_module.name,
                    "address": {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
                },
            )
            assert resp.status_code == 200
            market_config.refresh_from_db()
            assert market_config.source_url_type == ProductSourceUrlType.ENGINE_PROD_ENV

        # 切换独立域名
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/entrances/default/"
            resp = api_client.post(
                url,
                data={
                    "module": bk_module.name,
                    "address": {
                        'id': Domain.objects.get(environment_id=bk_prod_env.id).id,
                        'url': 'http://foo-custom.example.com/subpath/',
                        'type': 'custom',
                    },
                },
            )
            assert resp.status_code == 200
            market_config.refresh_from_db()
            assert market_config.source_url_type == ProductSourceUrlType.CUSTOM_DOMAIN
            assert market_config.custom_domain_url == 'http://foo-custom.example.com/subpath/'

        # 切换不存在的独立域名
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/entrances/default/"
            resp = api_client.post(
                url,
                data={
                    "module": bk_module.name,
                    "address": {
                        'id': Domain.objects.get(environment_id=bk_prod_env.id).id,
                        'url': 'http://foo-404.example.com/subpath/',
                        'type': 'custom',
                    },
                },
            )
            assert resp.status_code == 400
            assert resp.json() == {
                'code': 'CANNOT_SET_DEFAULT',
                'detail': '设置默认访问模块失败: http://foo-404.example.com/subpath/ 并非 default 模块的访问入口',
            }

    def test_switch_default_module(self, api_client, bk_user, bk_app, bk_module, bk_prod_env, bk_prod_wl_app):
        market_config, _ = MarketConfig.objects.get_or_create_by_app(bk_app)
        another_m = create_module(bk_app)
        create_pending_wl_apps(bk_app, cluster_name=CLUSTER_NAME_FOR_TESTING)
        another_prod_env = another_m.get_envs("prod")

        # 切换默认访问模块
        assert bk_app.get_default_module().name == bk_module.name
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/entrances/default/"
            resp = api_client.post(
                url,
                data={
                    "module": another_m.name,
                    "address": {'id': None, 'url': f'http://{bk_app.code}.example.com', 'type': 'subdomain'},
                },
            )
            assert resp.status_code == 200
            assert bk_app.get_default_module().name == another_m.name

        # setup data
        # source type: custom
        Domain.objects.create(
            name='foo-custom.example.com',
            path_prefix='/subpath/',
            module_id=bk_module.id,
            environment_id=bk_prod_env.id,
        )
        # 切换默认访问模块, 同时切换访问地址
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/entrances/default/"
            resp = api_client.post(
                url,
                data={
                    "module": bk_module.name,
                    "address": {
                        'id': Domain.objects.get(environment_id=bk_prod_env.id).id,
                        'url': 'http://foo-custom.example.com/subpath/',
                        'type': 'custom',
                    },
                },
            )

            assert resp.status_code == 200
            assert bk_app.get_default_module().name == bk_module.name
            market_config.refresh_from_db()
            assert market_config.source_url_type == ProductSourceUrlType.CUSTOM_DOMAIN
            assert market_config.custom_domain_url == 'http://foo-custom.example.com/subpath/'

        # 切换默认访问模块, 同时切换成独立域名
        # setup data
        # source type: custom
        Domain.objects.create(
            name='foo-another.example.com',
            path_prefix='/subpath/',
            module_id=another_m.id,
            environment_id=another_prod_env.id,
        )
        with override_region_configs(bk_app.region, set_subdomain_exposed_url_type):
            url = f"/api/bkapps/applications/{bk_app.code}/entrances/default/"
            resp = api_client.post(
                url,
                data={
                    "module": another_m.name,
                    "address": {
                        'id': Domain.objects.get(environment_id=another_prod_env.id).id,
                        'url': 'http://foo-another.example.com/subpath/',
                        'type': 'custom',
                    },
                },
            )

            assert resp.status_code == 200
            assert bk_app.get_default_module().name == another_m.name
            market_config.refresh_from_db()
            assert market_config.source_url_type == ProductSourceUrlType.CUSTOM_DOMAIN
            assert market_config.custom_domain_url == 'http://foo-another.example.com/subpath/'
