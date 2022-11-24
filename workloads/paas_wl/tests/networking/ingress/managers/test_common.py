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

from paas_wl.networking.ingress.entities.ingress import PIngressDomain
from paas_wl.networking.ingress.managers.common import SubpathCompatPlugin

pytestmark = [pytest.mark.django_db]


class TestSubpathCompatPlugin:
    @pytest.mark.parametrize(
        'paths,snippet_excerpts',
        [
            (['/'], ['X-Script-Name /']),
            (['/foo/'], [' or "/foo/"', 'proxy_set_header X-Script-Name $lua_x_script_name;']),
            (['/stag--foo/', '/bar/'], [' or "/bar/"', 'proxy_set_header X-Script-Name $lua_x_script_name;']),
        ],
    )
    def test_different_paths(self, paths, snippet_excerpts, app):
        domain = PIngressDomain(host='example.com', path_prefix_list=paths)
        plugin = SubpathCompatPlugin(app, domains=[domain])
        snippet = plugin.make_configuration_snippet()
        for excerpt in snippet_excerpts:
            assert excerpt in snippet

    def test_multiple_domains(self, app):
        domain = PIngressDomain(host='example.com', path_prefix_list=['/'])
        plugin = SubpathCompatPlugin(app, domains=[domain, domain])
        assert 'X-Script-Name /' in plugin.make_configuration_snippet()

    def test_empty_domains(self, app):
        plugin = SubpathCompatPlugin(app)
        assert plugin.make_configuration_snippet() == ''
