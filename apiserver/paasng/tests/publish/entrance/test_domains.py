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
import cattr
import pytest

from paasng.engine.controller.models import IngressConfig
from paasng.publish.entrance.domains import get_preallocated_domain

pytestmark = pytest.mark.django_db


class TestGetPreallocatedDomain:
    def test_not_configured(self):
        # Only subpath was configured
        domain = get_preallocated_domain(
            'test-code',
            ingress_config=cattr.structure(
                {'sub_path_domains': [{"name": 'sub.example.com'}, {"name": 'sub.example.cn'}]}, IngressConfig
            ),
        )
        assert domain is None

    @pytest.mark.parametrize(
        'https_enabled, expected_address',
        [
            (True, 'https://test-code.example.com'),
            (False, 'http://test-code.example.com'),
        ],
    )
    def test_enable_https(self, https_enabled, expected_address):
        domain = get_preallocated_domain(
            'test-code',
            ingress_config=cattr.structure(
                {
                    'app_root_domains': [
                        {"name": 'example.com', "https_enabled": https_enabled},
                        {"name": 'example.cn', "https_enabled": https_enabled},
                    ],
                },
                IngressConfig,
            ),
        )
        assert domain
        assert domain.prod.as_url().as_address() == expected_address

    def test_without_module_name(self):
        domain = get_preallocated_domain(
            'test-code', ingress_config=cattr.structure({'app_root_domains': [{"name": 'example.com'}]}, IngressConfig)
        )
        assert domain
        assert domain.stag.as_url().as_address() == 'http://stag-dot-test-code.example.com'
        assert domain.prod.as_url().as_address() == 'http://test-code.example.com'

    def test_with_module_name(self):
        domain = get_preallocated_domain(
            'test-code',
            ingress_config=cattr.structure({'app_root_domains': [{"name": 'example.com'}]}, IngressConfig),
            module_name='api',
        )
        assert domain
        assert domain.stag.as_url().as_address() == 'http://stag-dot-api-dot-test-code.example.com'
        assert domain.prod.as_url().as_address() == 'http://prod-dot-api-dot-test-code.example.com'
