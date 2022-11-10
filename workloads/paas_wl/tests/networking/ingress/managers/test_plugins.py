import pytest

from paas_wl.networking.ingress.managers import AppIngressMgr
from paas_wl.networking.ingress.plugins import override_plugins
from paas_wl.networking.ingress.plugins.ingress import IngressPlugin

pytestmark = [pytest.mark.django_db]


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
    def test_default_plugins(self, plugins, s_snippet, c_snippet, app):
        class FakePluginIngressMgr(AppIngressMgr):
            def make_ingress_name(self) -> str:
                return 'foo-ingress-test'

        with override_plugins(plugins):
            server_snippet = FakePluginIngressMgr(app).construct_server_snippet(domains=[])
            assert server_snippet == s_snippet

            configuration_snippet = FakePluginIngressMgr(app).construct_configuration_snippet(domains=[])
            assert configuration_snippet == c_snippet

    def test_extra_plugins(self, app):
        class FakePluginIngressMgr(AppIngressMgr):
            plugins = [ExtraStubPlugin]

            def make_ingress_name(self) -> str:
                return 'foo-ingress-test'

        with override_plugins([FooStubPlugin, BarStubPlugin]):
            server_snippet = FakePluginIngressMgr(app).construct_server_snippet(domains=[])
            assert server_snippet == 'foo-server\nbar-server\nextra-server'

            configuration_snippet = FakePluginIngressMgr(app).construct_configuration_snippet(domains=[])
            assert configuration_snippet == 'foo-configuration\nextra-configuration'
