from unittest import mock

import pytest

from paasng.engine.deploy.infra.models_utils import get_processes_by_build, update_engine_app_config

pytestmark = pytest.mark.django_db


def test_get_processes_by_build(bk_module):
    engine_app = bk_module.envs.get(environment='prod').engine_app
    fake_procfile = {
        'web': (
            'gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile - --access-logformat '
            '\'[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"\''
        )
    }
    with mock.patch("paasng.engine.deploy.engine_svc.EngineDeployClient.get_procfile", return_value=fake_procfile):
        assert 'web' in get_processes_by_build(engine_app=engine_app, build_id="fake-build-id")


class TestUpdateEngineAppConfig:
    """Test update_engine_app_config()"""

    def test_normal(self, bk_module, bk_deployment):
        with mock.patch('paasng.engine.deploy.infra.models_utils.EngineDeployClient') as mocked_client:
            update_engine_app_config(bk_module.get_envs("prod").engine_app, bk_deployment.version_info)
            assert mocked_client().update_config.called
