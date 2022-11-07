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
import cattr
import pytest

from paasng.engine.controller.models import IngressConfig
from paasng.publish.entrance.subpaths import ModuleEnvSubpaths, get_legacy_compatible_path, get_preallocated_path
from tests.utils.mocks.engine import replace_cluster_service

pytestmark = pytest.mark.django_db


class TestModuleEnvSubpaths:
    @pytest.fixture()
    def bk_app(self, bk_app):
        bk_app.code = 'some-app-o'
        bk_app.save()
        return bk_app

    @pytest.fixture(autouse=True)
    def setup_cluster(self):
        with replace_cluster_service(
            ingress_config={'sub_path_domains': [{"name": 'sub.example.com'}, {"name": 'sub.example.cn'}]}
        ):
            yield

    def test_prod_default(self, bk_module):
        env = bk_module.envs.get(environment='prod')
        subpaths = ModuleEnvSubpaths(env).all()
        legacy_path = get_legacy_compatible_path(env)
        assert [d.as_url().as_address() for d in subpaths] == [
            'http://sub.example.com/prod--default--some-app-o/',
            f'http://sub.example.com{legacy_path}',
            'http://sub.example.cn/prod--default--some-app-o/',
            f'http://sub.example.cn{legacy_path}',
            'http://sub.example.com/prod--some-app-o/',
            'http://sub.example.cn/prod--some-app-o/',
            'http://sub.example.com/some-app-o/',
            'http://sub.example.cn/some-app-o/',
        ]
        p = ModuleEnvSubpaths(env).get_shortest()
        assert p and p.as_url().as_address() == 'http://sub.example.cn/some-app-o/'

    def test_stag_default(self, bk_module):
        env = bk_module.envs.get(environment='stag')
        subpaths = ModuleEnvSubpaths(env).all()
        legacy_path = get_legacy_compatible_path(env)
        assert [d.as_url().as_address() for d in subpaths] == [
            'http://sub.example.com/stag--default--some-app-o/',
            f'http://sub.example.com{legacy_path}',
            'http://sub.example.cn/stag--default--some-app-o/',
            f'http://sub.example.cn{legacy_path}',
            'http://sub.example.com/stag--some-app-o/',
            'http://sub.example.cn/stag--some-app-o/',
        ]

    def test_stag_non_default(self, bk_module, bk_stag_env):
        bk_module.is_default = False
        bk_module.save()

        env = bk_stag_env
        subpaths = ModuleEnvSubpaths(env).all()
        legacy_path = get_legacy_compatible_path(env)
        assert [d.as_url().as_address() for d in subpaths] == [
            'http://sub.example.com/stag--default--some-app-o/',
            f'http://sub.example.com{legacy_path}',
            'http://sub.example.cn/stag--default--some-app-o/',
            f'http://sub.example.cn{legacy_path}',
        ]


class TestModuleEnvSubpathsNotConfigured:
    @pytest.fixture(autouse=True)
    def setup_cluster(self):
        with replace_cluster_service(ingress_config={'sub_path_domains': []}):
            yield

    def test_prod_default(self, bk_module):
        env = bk_module.envs.get(environment='prod')
        subpaths = ModuleEnvSubpaths(env).all()
        assert [d.as_url().as_address() for d in subpaths] == []


class TestGetPreallocatedPath:
    def test_no_module_name(self):
        subpath = get_preallocated_path(
            'test-code',
            ingress_config=cattr.structure(
                {'sub_path_domains': [{"name": 'sub.example.com'}, {"name": 'sub.example.cn'}]}, IngressConfig
            ),
        )
        assert subpath
        assert subpath.stag.as_url().as_address() == 'http://sub.example.com/stag--test-code/'
        assert subpath.prod.as_url().as_address() == 'http://sub.example.com/test-code/'

    def test_with_module_name(self):
        subpath = get_preallocated_path(
            'test-code',
            ingress_config=cattr.structure(
                {'sub_path_domains': [{"name": 'sub.example.com'}, {"name": 'sub.example.cn'}]}, IngressConfig
            ),
            module_name='api',
        )
        assert subpath
        assert subpath.stag.as_url().as_address() == 'http://sub.example.com/stag--api--test-code/'
        assert subpath.prod.as_url().as_address() == 'http://sub.example.com/prod--api--test-code/'

    def test_https(self):
        subpath = get_preallocated_path(
            'test-code',
            ingress_config=cattr.structure(
                {
                    'sub_path_domains': [
                        {"name": 'sub.example.com', 'https_enabled': True},
                        {"name": 'sub.example.cn'},
                    ],
                },
                IngressConfig,
            ),
        )
        assert subpath
        assert subpath.stag.as_url().as_address() == 'https://sub.example.com/stag--test-code/'
        assert subpath.prod.as_url().as_address() == 'https://sub.example.com/test-code/'


def test_get_legacy_compatible_path(bk_stag_env):
    module = bk_stag_env.module
    assert get_legacy_compatible_path(bk_stag_env) == f'/{module.region}-{bk_stag_env.engine_app.name}/'
