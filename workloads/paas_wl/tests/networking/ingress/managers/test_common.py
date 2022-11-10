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
