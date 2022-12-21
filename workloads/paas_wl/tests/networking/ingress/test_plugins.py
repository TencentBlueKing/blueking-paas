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

from paas_wl.networking.ingress.plugins.exceptions import PluginNotConfigured
from paas_wl.networking.ingress.plugins.ingress import AccessControlPlugin, PaasAnalysisPlugin
from paas_wl.platform.applications.models.managers.app_metadata import update_metadata

pytestmark = pytest.mark.django_db


class TestModuleAccessControll:
    def test_not_configured(self, app, settings):
        settings.SERVICES_PLUGINS = {}
        with pytest.raises(PluginNotConfigured):
            AccessControlPlugin(app).make_configuration_snippet()

    def test_acl_is_enabled_false(self, app):
        update_metadata(app, acl_is_enabled=False)
        assert AccessControlPlugin(app).make_configuration_snippet() == ''

    def test_configured_with_region(self, app, settings):
        update_metadata(app, acl_is_enabled=True)
        settings.SERVICES_PLUGINS = {
            'access_control': {
                '_lookup_field': 'region',
                'data': {
                    settings.FOR_TESTS_DEFAULT_REGION: {
                        'dj_admin_ip_range_map': 'inner',
                        'redis_server_name': 'local',
                    }
                },
            }
        }

        snippet = AccessControlPlugin(app).make_configuration_snippet()
        assert "set $acc_redis_server_name 'local';" in snippet
        assert "set $acc_dj_admin_ip_range 'inner';" in snippet

    def test_configured_without_region(self, app, settings):
        update_metadata(app, acl_is_enabled=True)
        settings.SERVICES_PLUGINS = {
            'access_control': {'dj_admin_ip_range_map': 'inner', 'redis_server_name': 'local'}
        }
        snippet = AccessControlPlugin(app).make_configuration_snippet()
        assert "set $acc_redis_server_name 'local';" in snippet
        assert "set $acc_dj_admin_ip_range 'inner';" in snippet


class TestPaasAnalysisPlugin:
    @pytest.fixture
    def app_with_metadata(self, app):
        update_metadata(app, bkpa_site_id=100)
        return app

    @pytest.mark.parametrize(
        'plugins_config,snippet_is_empty',
        [
            ({'enabled': True}, False),
            ({'enabled': False}, True),
            ({'foo': 'bar'}, True),
        ],
    )
    def test_different_config(self, plugins_config, snippet_is_empty, app_with_metadata, settings):
        settings.SERVICES_PLUGINS = {'paas_analysis': plugins_config}
        snippet = PaasAnalysisPlugin(app_with_metadata).make_configuration_snippet()
        if snippet_is_empty:
            assert snippet == ''
        else:
            assert 'set $bkpa_site_id 100;' in snippet

    def test_enabled_no_metadata(self, app, settings):
        settings.SERVICES_PLUGINS = {'paas_analysis': {'enabled': True}}
        module = PaasAnalysisPlugin(app)
        snippet = module.make_configuration_snippet()
        assert snippet == ''
