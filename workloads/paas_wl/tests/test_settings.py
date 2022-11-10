import os
from unittest import mock

import pytest
from blue_krill.encrypt.utils import encrypt_string
from dynaconf import LazySettings

from paas_wl.settings.utils import (
    get_database_conf,
    get_internal_services_jwt_auth_conf,
    get_paas_service_jwt_clients,
    is_redis_backend,
    is_redis_sentinel_backend,
)


@pytest.fixture
def settings():
    return LazySettings()


def test_get_database_from_url(settings):
    db_url = 'mysql://user:123456@127.0.0.0.1:3306/foo'
    with mock.patch.dict(os.environ, {"DATABASE_URL": encrypt_string(db_url)}, clear=True):
        db_conf = get_database_conf(settings)
        assert db_conf
        assert db_conf['USER'] == 'user'
        assert db_conf['NAME'] == 'foo'


@pytest.mark.parametrize(
    'for_tests,name',
    [(False, 'foo'), (True, 'test_foo')],
)
def test_get_database_for_tests(settings, for_tests, name):
    settings.update({'FOO_DATABASE_PORT': 3308, 'FOO_DATABASE_NAME': 'foo'})
    db_conf = get_database_conf(settings, env_var_prefix='FOO_', for_tests=for_tests)
    assert db_conf
    assert db_conf['NAME'] == name
    assert db_conf['PORT'] == 3308


def test_get_internal_services_jwt_auth_conf_simple(settings):
    settings.update({'INTERNAL_SERVICES_JWT_AUTH_CONF': None, 'ONE_SIMPLE_JWT_AUTH_KEY': 'foo-key'})
    assert get_internal_services_jwt_auth_conf(settings) == {
        'iss': 'paas-v3',
        'key': 'foo-key',
    }


def test_get_internal_services_jwt_auth_conf_normal(settings):
    settings.update(
        {
            'INTERNAL_SERVICES_JWT_AUTH_CONF': {
                'iss': 'paas-v3',
                'key': 'bar-key',
            },
            'ONE_SIMPLE_JWT_AUTH_KEY': None,
        }
    )
    assert get_internal_services_jwt_auth_conf(settings) == {
        'iss': 'paas-v3',
        'key': 'bar-key',
    }


def test_get_paas_service_jwt_clients_simple(settings):
    settings.update({'PAAS_SERVICE_JWT_CLIENTS': None, 'ONE_SIMPLE_JWT_AUTH_KEY': 'foo-key'})
    assert dict(get_paas_service_jwt_clients(settings)[0]) == {
        'iss': 'paas-v3',
        'key': 'foo-key',
    }


def test_get_paas_service_jwt_clients_mixed(settings):
    settings.update(
        {
            'PAAS_SERVICE_JWT_CLIENTS': [{'iss': 'paas-v3', 'key': 'bar-key'}],
            'ONE_SIMPLE_JWT_AUTH_KEY': 'foo-key',
        }
    )
    assert [c['key'] for c in get_paas_service_jwt_clients(settings)] == ['bar-key', 'foo-key']


@pytest.mark.parametrize(
    'url,result',
    [
        ('redis://...', True),
        ('amqp://...', False),
        ('sentinel://...', True),
        (['redis://...', 'redis://...'], True),
    ],
)
def test_is_redis_backend(url, result):
    assert is_redis_backend(url) is result


@pytest.mark.parametrize(
    'url,result',
    [
        ('redis://...', False),
        ('amqp://...', False),
        ('sentinel://...', True),
        ('sentine1://...', False),
        (['redis://...', 'redis://...'], False),
    ],
)
def test_is_redis_sentinel_backend(url, result):
    assert is_redis_sentinel_backend(url) is result
