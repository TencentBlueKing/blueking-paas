import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db

# Short name
REGION = settings.FOR_TESTS_DEFAULT_REGION


class TestAppModelResourceViewSet:
    def test_create(self, api_client, bk_app, bk_module):
        response = api_client.post(
            f'/regions/{REGION}/app_model_resources/',
            data={
                'application_id': bk_app.id,
                'module_id': bk_module.id,
                'code': bk_app.code,
                'image': 'nginx:latest',
            },
        )
        assert response.status_code == 201
        resp = response.json()
        assert resp['module_id'] == str(bk_module.id)
        assert resp['manifest']['kind'] == 'BkApp'

    def test_create_duplicated(self, api_client, bk_app, bk_module):
        def _create():
            return api_client.post(
                f'/regions/{REGION}/app_model_resources/',
                data={
                    'application_id': bk_app.id,
                    'module_id': bk_module.id,
                    'code': bk_app.code,
                    'image': 'nginx:latest',
                },
            )

        resp = _create()
        assert resp.status_code == 201
        resp_dup = _create()
        assert resp_dup.status_code == 400
