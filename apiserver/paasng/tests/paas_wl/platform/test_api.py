import pytest
from django.conf import settings

from paas_wl.platform.api import create_app_ignore_duplicated, get_metadata_by_env, update_metadata_by_env

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.django_db(databases=["workloads"], transaction=True)
def test_create_app_ignore_duplicated():
    info = create_app_ignore_duplicated(settings.FOR_TESTS_DEFAULT_REGION, 'foo-app', 'default')
    assert info.name == 'foo-app'

    # Create again with the same name
    recreated_info = create_app_ignore_duplicated(settings.FOR_TESTS_DEFAULT_REGION, 'foo-app', 'default')
    assert recreated_info.uuid == info.uuid


def test_metadata_funcs(bk_app, bk_stag_env, with_wl_apps):
    assert get_metadata_by_env(bk_stag_env).paas_app_code == bk_app.code
    update_metadata_by_env(bk_stag_env, {'paas_app_code': 'foo-updated'})
    assert get_metadata_by_env(bk_stag_env).paas_app_code == 'foo-updated'
