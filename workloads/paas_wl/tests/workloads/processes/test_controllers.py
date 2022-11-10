# -*- coding: utf-8 -*-
import pytest

from paas_wl.workloads.processes.controllers import env_is_running
from tests.cnative.specs.conftest import create_cnative_deploy
from tests.workloads.conftest import create_release

pytestmark = pytest.mark.django_db


class Test__env_is_running:
    def test_default(self, bk_app, bk_stag_env, bk_user):
        assert env_is_running(bk_stag_env) is False
        # Create a failed release at first, it should not affect the result
        create_release(bk_stag_env, bk_user, failed=True)
        assert env_is_running(bk_stag_env) is False

        create_release(bk_stag_env, bk_user, failed=False)
        assert env_is_running(bk_stag_env) is True

    def test_cnative(self, cnative_bk_app, bk_stag_env, bk_user):
        assert env_is_running(bk_stag_env) is False

        create_cnative_deploy(bk_stag_env, bk_user)
        assert env_is_running(bk_stag_env) is True
