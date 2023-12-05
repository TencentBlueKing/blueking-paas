import pytest

from paas_wl.workloads.networking.sync import sync_proc_ingresses

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.usefixtures("_with_wl_apps"),
]


def test_sync_proc_ingresses(bk_stag_env):
    # TODO: make stag env as running as add more test cases
    sync_proc_ingresses(bk_stag_env)
