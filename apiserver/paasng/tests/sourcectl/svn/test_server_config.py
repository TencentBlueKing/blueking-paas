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
import pytest

from paasng.dev_resources.sourcectl.source_types import refresh_sourcectl_types
from paasng.dev_resources.sourcectl.svn.server_config import BkSvnServerConfig, get_bksvn_config


@pytest.fixture
def server_config_factory():
    def _factory():
        return {
            '_lookup_field': 'region',
            'data': {
                'r1': {
                    "base_url": 'svn://127.0.0.1:3690/r1_base',
                    "legacy_base_url": 'svn://127.0.0.1:3690/r1_legacy_base',
                    "su_name": 'r1_user',
                    "su_pass": 'r1_pass',
                    "need_security": False,
                    "admin_url": "127.0.0.1:3690/r1_admin",
                },
                'r2': {
                    "base_url": 'svn://127.0.0.1:3690/r2_base',
                    "legacy_base_url": 'svn://127.0.0.1:3690/r2_legacy_base',
                    "su_name": 'r2_user',
                    "su_pass": 'r2_pass',
                    "need_security": True,
                    "admin_url": "127.0.0.1:3690/r2_admin",
                },
            },
        }

    return _factory


class TestBkSvnConfig:
    def test_get_base_path(self, server_config_factory):
        config = BkSvnServerConfig(**server_config_factory()['data']['r1'])
        assert config.get_base_path() == '/r1_base'


class TestGetBkSvnConfig:
    @pytest.mark.parametrize(
        'region,base_url',
        [
            ('r1', 'svn://127.0.0.1:3690/r1_base'),
            ('r2', 'svn://127.0.0.1:3690/r2_base'),
        ],
    )
    def test_single_svn(self, region, base_url, server_config_factory):
        source_type_spec_configs = [
            {
                'spec_cls': 'paasng.dev_resources.sourcectl.type_specs.BkSvnSourceTypeSpec',
                'attrs': {'name': 'bk_svn_1', 'server_config': server_config_factory()},
            },
        ]
        refresh_sourcectl_types(source_type_spec_configs)
        assert get_bksvn_config(region).base_url == base_url

    def test_multi_svn(self, settings, server_config_factory):
        server_config_copy = server_config_factory()
        server_config_copy['data']['r1']['base_url'] = 'http://modified-base/'
        source_type_spec_configs = [
            {
                'spec_cls': 'paasng.dev_resources.sourcectl.type_specs.BkSvnSourceTypeSpec',
                'attrs': {'name': 'bk_svn_1', 'server_config': server_config_factory()},
            },
            {
                'spec_cls': 'paasng.dev_resources.sourcectl.type_specs.BkSvnSourceTypeSpec',
                'attrs': {'name': 'bk_svn_2', 'server_config': server_config_copy},
            },
        ]
        refresh_sourcectl_types(source_type_spec_configs)
        assert get_bksvn_config('r1').base_url == 'svn://127.0.0.1:3690/r1_base'
        assert get_bksvn_config('r1', name='bk_svn_2').base_url == 'http://modified-base/'
