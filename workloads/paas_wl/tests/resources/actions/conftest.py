from unittest import mock

import pytest


@pytest.fixture
def mock_run_command():
    with mock.patch("paas_wl.resources.base.client.K8sScheduler.run_command"):
        yield
