import pytest

from paas_wl.cnative.specs.models import create_app_resource
from paas_wl.cnative.specs.procs import CNativeProcSpec, parse_proc_specs
from paas_wl.workloads.processes.constants import AppEnvName

pytestmark = pytest.mark.django_db


class TestParseProcSpecs:
    def test_default(self, bk_app):
        res = create_app_resource(bk_app.name, 'busybox')
        assert parse_proc_specs(res, AppEnvName.STAG) == [CNativeProcSpec('web', 1, 'start')]

    def test_stopped(self, bk_app):
        res = create_app_resource(bk_app.name, 'busybox')
        res.spec.processes[0].replicas = 0
        assert parse_proc_specs(res, AppEnvName.STAG) == [CNativeProcSpec('web', 0, 'stop')]
