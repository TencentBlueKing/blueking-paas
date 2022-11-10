# -*- coding: utf-8 -*-
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
