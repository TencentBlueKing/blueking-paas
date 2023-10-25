import pytest

from paas_wl.bk_app.applications.api import get_latest_build_id
from paas_wl.bk_app.applications.models.build import Build

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_get_latest_build_id(bk_stag_env, with_wl_apps):
    assert get_latest_build_id(bk_stag_env) is None
    Build.objects.create(app=bk_stag_env.wl_app)
    assert get_latest_build_id(bk_stag_env) is not None
