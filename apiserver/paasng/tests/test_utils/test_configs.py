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
from dataclasses import dataclass

import pytest

from paasng.utils.configs import RegionAwareConfig, get_region_aware


@pytest.fixture
def config_with_region():
    return {
        '_lookup_field': 'region',
        'data': {'r1': {'url': 'r1.com'}, 'r2': {'url': 'r2.com'}},
    }


class TestRegionAwareConfig:
    @pytest.mark.parametrize(
        'user_settings,expected_config',
        [
            ({'url': 'http://example.com'}, {'url': 'http://example.com'}),
            (['foo', 'bar'], ['foo', 'bar']),
        ],
    )
    def test_no_region(self, user_settings, expected_config):
        config = RegionAwareConfig(user_settings)
        assert config.get('foo') == expected_config

    def test_region(self, config_with_region):
        config = RegionAwareConfig(config_with_region)
        assert config.get('r1') == {'url': 'r1.com'}
        assert config.get('r2') == {'url': 'r2.com'}

    def test_region_not_found(self, config_with_region):
        config = RegionAwareConfig(config_with_region)
        with pytest.raises(KeyError):
            config.get('r100')

    def test_region_not_found_default(self, config_with_region):
        config = RegionAwareConfig(config_with_region)
        assert config.get('r100', use_default_value=True) is not None


@dataclass
class FooConfig:
    key: str
    value: str


@pytest.mark.parametrize(
    'region,result_cls,expected_result',
    [
        ('r1', None, {'key': 'r1', 'value': 'r1-value'}),
        ('r1', FooConfig, FooConfig('r1', 'r1-value')),
    ],
)
def test_get_region_aware(region, result_cls, expected_result, settings):
    settings.FOO_CONFIG = {
        '_lookup_field': 'region',
        'data': {
            'r1': {'key': 'r1', 'value': 'r1-value'},
            'r2': {'key': 'r2', 'value': 'r2-value'},
        },
    }
    assert get_region_aware('FOO_CONFIG', region, result_cls=result_cls) == expected_result
