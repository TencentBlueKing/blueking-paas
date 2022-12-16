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

from paas_wl.networking.ingress.addrs import Address, AddressType, EnvAddresses
from paas_wl.networking.ingress.constants import AppDomainSource, AppSubpathSource
from paas_wl.networking.ingress.models import AppDomain, AppSubpath, Domain
from paas_wl.platform.applications.models import EngineApp
from tests.workloads.conftest import create_release

pytestmark = pytest.mark.django_db


class TestEnvAddresses:
    @pytest.fixture(autouse=True)
    def _setup_data(self, bk_module, bk_stag_env):
        engine_app = EngineApp.objects.get_by_env(bk_stag_env)

        # Create all types of domains
        # source type: subdomain
        AppDomain.objects.create(app=engine_app, host='foo.example.com', source=AppDomainSource.AUTO_GEN)
        AppDomain.objects.create(app=engine_app, host='foo-more.example.org', source=AppDomainSource.AUTO_GEN)
        AppDomain.objects.create(app=engine_app, host='foo.example.org', source=AppDomainSource.AUTO_GEN)
        # source type: subpath
        AppSubpath.objects.create(app=engine_app, subpath='/foo/', source=AppSubpathSource.DEFAULT)
        # source type: custom
        Domain.objects.create(
            name='foo-custom.example.com', path_prefix='/', module_id=bk_module.id, environment_id=bk_stag_env.id
        )

    def test_not_deployed(self, bk_stag_env):
        addrs = EnvAddresses(bk_stag_env).get()
        assert addrs == []

    def test_integrated(self, bk_user, bk_stag_env, patch_ingress_config):
        """Integrated test with multiple subpath domains and customized ports"""
        patch_ingress_config(
            app_root_domains=[
                {"name": "foo.example.com", 'reserved': True},
            ],
            sub_path_domains=[
                {"name": "p1.example.com", 'https_enabled': True, 'reserved': True},
                {"name": "p2.example.com", 'https_enabled': False},
            ],
            port_map={'http': '8080', 'https': 443},
        )

        # Create a successful release record to by-paas deployment check
        create_release(bk_stag_env, bk_user, failed=False)
        addrs = EnvAddresses(bk_stag_env).get()
        assert addrs == [
            Address(AddressType.SUBDOMAIN, 'http://foo.example.org:8080/', False),
            Address(AddressType.SUBDOMAIN, 'http://foo-more.example.org:8080/', False),
            Address(AddressType.SUBDOMAIN, 'http://foo.example.com:8080/', True),
            Address(AddressType.SUBPATH, 'http://p2.example.com:8080/foo/', False),
            Address(AddressType.SUBPATH, 'https://p1.example.com/foo/', True),
            Address(AddressType.CUSTOM, 'http://foo-custom.example.com:8080/', False),
        ]
