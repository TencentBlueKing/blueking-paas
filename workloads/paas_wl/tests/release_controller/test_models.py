# -*- coding: utf-8 -*-
import pytest

from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.utils.constants import BuildStatus

pytestmark = pytest.mark.django_db


class TestInterruptionAllowed:
    def test_default(self, bp: BuildProcess):
        assert bp.check_interruption_allowed() is False

    def test_set_true(self, bp: BuildProcess):
        bp.set_logs_was_ready()
        assert bp.check_interruption_allowed() is True

    def test_finished_status(self, bp: BuildProcess):
        bp.status = BuildStatus.SUCCESSFUL
        bp.save(update_fields=['status'])
        bp.set_logs_was_ready()
        assert bp.check_interruption_allowed() is False
