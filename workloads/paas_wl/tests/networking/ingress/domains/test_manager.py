from unittest import mock

import pytest
from rest_framework.exceptions import ValidationError

from paas_wl.networking.ingress.domains.manager import CNativeCustomDomainManager, check_domain_used_by_market
from paas_wl.networking.ingress.models import Domain
from paas_wl.utils.error_codes import APIError
from tests.cnative.specs.conftest import create_cnative_deploy
from tests.utils.mocks.platform import FakePlatformSvcClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _setup_clients():
    with mock.patch('paas_wl.platform.external.client._global_plat_client', new=FakePlatformSvcClient()):
        yield


@pytest.mark.parametrize(
    'entrance_data,ret',
    [
        ({'entrance': None}, False),
        ({'entrance': {'type': 2, 'address': None}}, False),
        ({'entrance': {'type': 2, 'address': 'http://foo.com/'}}, True),
        ({'entrance': {'type': 2, 'address': 'http://foo-bar.com/'}}, False),
    ],
)
def test_check_domain_used_by_market(bk_app, entrance_data, ret):
    hostname = 'foo.com'
    with FakePlatformSvcClient.get_market_entrance.mock(return_value=entrance_data):
        assert check_domain_used_by_market(bk_app, hostname) is ret


class TestCNativeDftCustomDomainManager:
    def test_create_no_deploys(self, cnative_bk_app, bk_stag_env, bk_user):
        mgr = CNativeCustomDomainManager(cnative_bk_app)
        with pytest.raises(ValidationError):
            mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def test_create_successfully(self, mocker, cnative_bk_app, bk_stag_env, bk_user):
        mgr = CNativeCustomDomainManager(cnative_bk_app)
        # Create a successful deploy
        create_cnative_deploy(bk_stag_env, bk_user)
        domain = mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

        assert mocker.called
        assert domain is not None

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking', side_effect=ValueError('foo'))
    def test_create_failed(self, _mocker, cnative_bk_app, bk_stag_env, bk_user):
        mgr = CNativeCustomDomainManager(cnative_bk_app)
        # Create a successful deploy
        create_cnative_deploy(bk_stag_env, bk_user)
        with pytest.raises(APIError):
            mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

    @pytest.fixture
    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def domain_foo_com(self, _mocker, cnative_bk_app, bk_stag_env, bk_user) -> Domain:
        """Create a Domain fixture"""
        mgr = CNativeCustomDomainManager(cnative_bk_app)
        # Create a successful deploy
        create_cnative_deploy(bk_stag_env, bk_user)
        return mgr.create(env=bk_stag_env, host='foo.example.com', path_prefix='/', https_enabled=False)

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def test_update(self, mocker, cnative_bk_app, bk_stag_env, domain_foo_com):
        assert Domain.objects.get(environment_id=bk_stag_env.id).name == 'foo.example.com'
        CNativeCustomDomainManager(cnative_bk_app).update(
            domain_foo_com, host='bar.example.com', path_prefix='/', https_enabled=False
        )
        assert mocker.called
        assert Domain.objects.get(environment_id=bk_stag_env.id).name == 'bar.example.com'

    @mock.patch('paas_wl.networking.ingress.domains.manager.deploy_networking')
    def test_delete(self, mocker, cnative_bk_app, domain_foo_com):
        assert Domain.objects.count() == 1
        CNativeCustomDomainManager(cnative_bk_app).delete(domain_foo_com)
        assert mocker.called
        assert Domain.objects.count() == 0
