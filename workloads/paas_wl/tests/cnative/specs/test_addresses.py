from unittest import mock

import pytest
from cattr import structure

from paas_wl.cnative.specs.addresses import AddrResourceManager
from paas_wl.cnative.specs.addresses import Domain as MappingDomain
from paas_wl.cnative.specs.addresses import ExposedUrl, save_addresses, to_domain, to_shared_tls_domain
from paas_wl.networking.ingress.constants import AppDomainSource, AppSubpathSource
from paas_wl.networking.ingress.models import AppDomain, AppDomainSharedCert, AppSubpath, Domain
from paas_wl.platform.applications.models.app import EngineApp
from tests.utils.mocks.platform import FakePlatformSvcClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _setup_clients():
    with mock.patch('paas_wl.platform.external.client._global_plat_client', new=FakePlatformSvcClient()):
        yield


def test_save_addresses(bk_stag_env):
    engine_app = EngineApp.objects.get_by_env(bk_stag_env)
    assert AppDomain.objects.filter(app=engine_app).count() == 0
    assert AppSubpath.objects.filter(app=engine_app).count() == 0

    save_addresses(bk_stag_env)
    assert AppDomain.objects.filter(app=engine_app).count() == 1
    assert AppSubpath.objects.filter(app=engine_app).count() == 1


@pytest.mark.auto_create_ns
class TestToDomain:
    @pytest.mark.parametrize(
        'host,https_enabled,secret_name_has_value',
        [
            ('x-foo.example.com', False, False),
            ('not-match.example.com', True, False),
            ('x-foo.example.com', True, True),
        ],
    )
    def test_with_https(self, host, https_enabled, secret_name_has_value, bk_stag_engine_app):
        # Create a shared cert object
        AppDomainSharedCert.objects.create(
            region=bk_stag_engine_app.region, name="foo", cert_data="", key_data="", auto_match_cns="*-foo.example.com"
        )
        d = AppDomain.objects.create(
            app=bk_stag_engine_app,
            host=host,
            source=AppDomainSource.AUTO_GEN,
            https_enabled=https_enabled,
        )

        domain = to_domain(d)
        if secret_name_has_value:
            assert domain.tlsSecretName is not None
            assert len(domain.tlsSecretName) > 0
        else:
            assert domain.tlsSecretName is None


@pytest.mark.auto_create_ns
class TestToSharedTLSDomain:
    def test_normal(self, app):
        d = MappingDomain(host='x-foo.example.com', pathPrefixList=['/'])
        d = to_shared_tls_domain(d, app)
        assert d.tlsSecretName is None

        # Create a shared cert object
        AppDomainSharedCert.objects.create(
            region=app.region, name="foo", cert_data="", key_data="", auto_match_cns="*-foo.example.com"
        )
        d = to_shared_tls_domain(d, app)
        assert d.tlsSecretName is not None
        assert len(d.tlsSecretName) > 0


class TestAddrResourceManager:
    def test_integrated(self, bk_module, bk_stag_env):
        engine_app = EngineApp.objects.get_by_env(bk_stag_env)

        # Create all types of domains
        # source type: subdomain
        AppDomain.objects.create(app=engine_app, host='foo-subdomain.example.com', source=AppDomainSource.AUTO_GEN)
        # source type: subpath
        AppSubpath.objects.create(app=engine_app, subpath='/foo-subpath/', source=AppSubpathSource.DEFAULT)
        # source type: custom
        Domain.objects.create(
            name='foo-custom.example.com', path_prefix='/', module_id=bk_module.id, environment_id=bk_stag_env.id
        )

        addr_mgr = AddrResourceManager(bk_stag_env)
        mapping = addr_mgr.build_mapping()
        assert len(mapping.spec.data) == 3

        # Remove all types of domains
        AppDomain.objects.all().delete()
        AppSubpath.objects.all().delete()
        Domain.objects.all().delete()
        mapping = addr_mgr.build_mapping()
        assert len(mapping.spec.data) == 0


@pytest.mark.parametrize(
    "given, expected",
    [
        ({"host": "www.example.com", "https_enabled": True}, "https://www.example.com"),
        ({"host": "www.example.com", "https_enabled": False}, "http://www.example.com"),
        ({"subpath": "", "host": "www.example.com", "https_enabled": True}, "https://www.example.com"),
        ({"subpath": "", "host": "www.example.com", "https_enabled": False}, "http://www.example.com"),
        ({"subpath": "/foo", "host": "www.example.com", "https_enabled": True}, "https://www.example.com/foo"),
        ({"subpath": "/foo", "host": "www.example.com", "https_enabled": False}, "http://www.example.com/foo"),
    ],
)
def test_exposed_url(given, expected):
    assert structure(given, ExposedUrl).as_url() == expected
