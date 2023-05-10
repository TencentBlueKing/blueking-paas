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

from paas_wl.networking.ingress.managers import AppIngressMgr
from paas_wl.networking.ingress.plugins import override_plugins
from paas_wl.networking.ingress.plugins.ingress import IngressPlugin

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class FooStubPlugin(IngressPlugin):
    def make_server_snippet(self) -> str:
        return 'foo-server'

    def make_configuration_snippet(self) -> str:
        return 'foo-configuration'


class BarStubPlugin(IngressPlugin):
    def make_server_snippet(self) -> str:
        return 'bar-server'


class ExtraStubPlugin(IngressPlugin):
    def make_server_snippet(self) -> str:
        return 'extra-server'

    def make_configuration_snippet(self) -> str:
        return 'extra-configuration'


class TestPlugins:
    @pytest.mark.parametrize(
        'plugins,s_snippet, c_snippet',
        [
            ([FooStubPlugin], 'foo-server', 'foo-configuration'),
            ([FooStubPlugin, BarStubPlugin], 'foo-server\nbar-server', 'foo-configuration'),
        ],
    )
    def test_default_plugins(self, plugins, s_snippet, c_snippet, bk_stag_wl_app):
        class FakePluginIngressMgr(AppIngressMgr):
            def make_ingress_name(self) -> str:
                return 'foo-ingress-test'

        with override_plugins(plugins):
            server_snippet = FakePluginIngressMgr(bk_stag_wl_app).construct_server_snippet(domains=[])
            assert server_snippet == s_snippet

            configuration_snippet = FakePluginIngressMgr(bk_stag_wl_app).construct_configuration_snippet(domains=[])
            assert configuration_snippet == c_snippet

    def test_extra_plugins(self, bk_stag_wl_app):
        class FakePluginIngressMgr(AppIngressMgr):
            plugins = [ExtraStubPlugin]

            def make_ingress_name(self) -> str:
                return 'foo-ingress-test'

        with override_plugins([FooStubPlugin, BarStubPlugin]):
            server_snippet = FakePluginIngressMgr(bk_stag_wl_app).construct_server_snippet(domains=[])
            assert server_snippet == 'foo-server\nbar-server\nextra-server'

            configuration_snippet = FakePluginIngressMgr(bk_stag_wl_app).construct_configuration_snippet(domains=[])
            assert configuration_snippet == 'foo-configuration\nextra-configuration'
