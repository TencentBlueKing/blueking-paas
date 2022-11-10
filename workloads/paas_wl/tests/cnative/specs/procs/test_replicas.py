import pytest

from paas_wl.cnative.specs.procs.exceptions import ProcNotDeployed, ProcNotFoundInRes
from paas_wl.cnative.specs.procs.replicas import ProcReplicas

pytestmark = pytest.mark.django_db


@pytest.mark.skip_when_no_crds
class TestProcReplicas:
    def test_not_deployed(self, bk_stag_env):
        with pytest.raises(ProcNotDeployed):
            ProcReplicas(bk_stag_env).scale('web', 1)

    def test_proc_not_found(self, bk_stag_env, deploy_stag_env):
        with pytest.raises(ProcNotFoundInRes):
            ProcReplicas(bk_stag_env).scale('invalid-name', 1)

    def test_get(self, bk_stag_env, deploy_stag_env):
        assert ProcReplicas(bk_stag_env).get('web') == 1

    def test_get_with_overlay_integrated(self, bk_stag_env, deploy_stag_env):
        assert ProcReplicas(bk_stag_env).get_with_overlay('web') == (1, False)
        ProcReplicas(bk_stag_env).scale('web', 2)
        assert ProcReplicas(bk_stag_env).get_with_overlay('web') == (2, True)
