import pytest

from paas_wl.workloads.networking.sync import sync_proc_ingresses

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_sync_proc_ingresses(bk_stag_env, with_wl_apps):
    # TODO: make stag env as running as add more test cases
    sync_proc_ingresses(bk_stag_env)
