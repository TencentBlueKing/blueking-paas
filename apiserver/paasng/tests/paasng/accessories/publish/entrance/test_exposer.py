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
"""Testcases entrance.exposer module
"""

import pytest

from paas_wl.workloads.networking.entrance.addrs import Address
from paas_wl.workloads.networking.entrance.constants import AddressType
from paasng.accessories.publish.entrance.exposer import env_is_deployed, get_exposed_url
from paasng.platform.modules.constants import ExposedURLType
from tests.utils.helpers import override_region_configs

pytestmark = pytest.mark.django_db


@pytest.fixture()
def _setup_addrs(bk_app, mock_env_is_running, mock_get_builtin_addresses):
    """Set up common mock and configs for testing functions related with addresses"""

    def update_region_hook(config):
        config["basic_info"]["link_engine_app"] = "http://example.com/{region}-legacy-path/"

    mock_env_is_running["stag"] = True
    mock_get_builtin_addresses["stag"] = [
        Address(type=AddressType.SUBDOMAIN, url="http://foo.example.com/"),
        Address(type=AddressType.SUBDOMAIN, url="http://default-foo.example.com/"),
        Address(type=AddressType.SUBDOMAIN, url="http://default-foo.example.org/"),
    ]
    with override_region_configs(bk_app.region, update_region_hook):
        yield


def test_env_is_deployed(bk_stag_env, bk_prod_env, mock_env_is_running):
    # See setup_addrs for details
    mock_env_is_running[bk_stag_env] = True
    mock_env_is_running[bk_prod_env] = False
    assert env_is_deployed(bk_stag_env) is True
    assert env_is_deployed(bk_prod_env) is False


class TestGetExposedUrl:
    def test_not_running(self, bk_prod_env, mock_env_is_running, mock_get_builtin_addresses):
        mock_env_is_running[bk_prod_env] = False
        assert get_exposed_url(bk_prod_env) is None

    @pytest.mark.usefixtures("_setup_addrs")
    @pytest.mark.parametrize(
        ("preferred_root", "expected"),
        [
            (None, "http://foo.example.com/"),
            ("example.org", "http://default-foo.example.org/"),
            # An invalid preferred root domain should have no effect
            ("invalid-example.com", "http://foo.example.com/"),
        ],
    )
    def test_preferred_root(self, preferred_root, expected, bk_module, bk_stag_env):
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN
        bk_module.user_preferred_root_domain = preferred_root
        bk_module.save()

        url = get_exposed_url(bk_stag_env)
        assert url is not None
        assert url.provider_type == "subdomain"
        assert url.address == expected
