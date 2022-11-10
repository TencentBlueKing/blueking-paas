import copy

import pytest

from paas_wl.cnative.specs.models import create_app_resource
from paas_wl.cnative.specs.procs.differ import ProcReplicasChange, diff_replicas
from paas_wl.workloads.processes.constants import AppEnvName

pytestmark = pytest.mark.django_db


class TestDiffReplicas:
    def test_same(self, bk_app):
        res = create_app_resource(bk_app.name, 'busybox')
        assert diff_replicas(res, res, AppEnvName.STAG) == []

    def test_changed(self, bk_app):
        res = create_app_resource(bk_app.name, 'busybox')
        res_new = copy.deepcopy(res)
        res_new.spec.processes[0].replicas = 3
        assert diff_replicas(res, res_new, AppEnvName.STAG) == [ProcReplicasChange('web', 1, 3)]
