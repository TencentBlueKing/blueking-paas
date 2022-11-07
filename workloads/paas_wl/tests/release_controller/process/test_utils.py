# -*- coding: utf-8 -*-
import pytest

from paas_wl.release_controller.process.utils import ProcessesSnapshotStore

pytestmark = pytest.mark.django_db


class TestProcessesSnapshotStore:
    def test_save_then_get(self, app, process):
        store = ProcessesSnapshotStore(app)
        store.save([process])
        assert store.get() == [process]
