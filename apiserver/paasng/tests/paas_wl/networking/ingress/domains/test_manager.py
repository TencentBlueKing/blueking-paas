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
from rest_framework.exceptions import ValidationError

from paas_wl.networking.ingress.domains.manager import CNativeCustomDomainManager, check_domain_used_by_market
from paas_wl.networking.ingress.models import Domain
from paas_wl.utils.error_codes import APIError
from paasng.platform.modules.constants import ExposedURLType
from paasng.publish.entrance.exposer import ModuleLiveAddrs
from tests.paas_wl.cnative.specs.utils import create_cnative_deploy

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.parametrize(
    'url_type, hostname, address_data, expected',
    [
        (ExposedURLType.SUBPATH, "foo.com", {"type": "subdomain", "url": "https://bar.foo.com"}, False),
        (ExposedURLType.SUBPATH, "bar.foo.com", {"type": "subdomain", "url": "https://bar.foo.com"}, False),
        (ExposedURLType.SUBPATH, "foo.com", {"type": "subpath", "url": "https://foo.com/bar"}, True),
        (ExposedURLType.SUBDOMAIN, "foo.com", {"type": "subdomain", "url": "https://bar.foo.com"}, False),
        (ExposedURLType.SUBDOMAIN, "bar.foo.com", {"type": "subdomain", "url": "https://bar.foo.com"}, True),
        (ExposedURLType.SUBDOMAIN, "foo.com", {"type": "subpath", "url": "https://foo.com/bar"}, False),
    ],
)
def test_check_domain_used_by_market(bk_app, bk_module, url_type, hostname, address_data, expected):
    bk_module.exposed_url_type = url_type
    bk_module.save()
    bk_app.refresh_from_db()

    # TODO: 重构 ControllerClient 时修改后移除这个 mock
    with mock.patch('paasng.publish.entrance.exposer.get_live_addresses') as mocker:
        mocker.return_value = ModuleLiveAddrs(
            [
                {
                    "env": "prod",
                    "is_running": True,
                    "addresses": [address_data],
                },
            ]
        )
        assert check_domain_used_by_market(bk_app, hostname) == expected


class TestCNativeDftCustomDomainManager:
    def test_create_no_deploys(self, bk_cnative_app, bk_stag_env, bk_stag_wl_app):
        mgr = CNativeCustomDomainManager(bk_cnative_app)
        with pytest.raises(ValidationError):
            mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def test_create_successfully(self, mocker, bk_cnative_app, bk_stag_env, bk_stag_wl_app, bk_user):
        mgr = CNativeCustomDomainManager(bk_cnative_app)
        # Create a successful deploy
        create_cnative_deploy(bk_stag_env, bk_user)
        domain = mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

        assert mocker.called
        assert domain is not None

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking', side_effect=ValueError('foo'))
    def test_create_failed(self, _mocker, bk_cnative_app, bk_stag_env, bk_stag_wl_app, bk_user):
        mgr = CNativeCustomDomainManager(bk_cnative_app)
        # Create a successful deploy
        create_cnative_deploy(bk_stag_env, bk_user)
        with pytest.raises(APIError):
            mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

    @pytest.fixture
    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def domain_foo_com(self, _mocker, bk_cnative_app, bk_stag_env, bk_stag_wl_app, bk_prod_wl_app, bk_user) -> Domain:
        """Create a Domain fixture"""
        mgr = CNativeCustomDomainManager(bk_cnative_app)
        # Create a successful deploy
        create_cnative_deploy(bk_stag_env, bk_user)
        domain = mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)
        return domain

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def test_update(self, mocker, bk_cnative_app, bk_stag_env, domain_foo_com):
        assert Domain.objects.get(environment_id=bk_stag_env.id).name == 'foo.example.com'
        CNativeCustomDomainManager(bk_cnative_app).update(
            domain_foo_com, host='bar.example.com', path_prefix='/', https_enabled=False
        )
        assert mocker.called
        assert Domain.objects.get(environment_id=bk_stag_env.id).name == 'bar.example.com'

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def test_delete(self, mocker, bk_cnative_app, domain_foo_com):
        assert Domain.objects.count() == 1
        CNativeCustomDomainManager(bk_cnative_app).delete(domain_foo_com)
        assert mocker.called
        assert Domain.objects.count() == 0
