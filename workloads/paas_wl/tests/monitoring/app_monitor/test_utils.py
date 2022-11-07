# -*- coding: utf-8 -*-
import pytest
from django_dynamic_fixture import G

from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.monitoring.app_monitor.utils import build_monitor_port

pytestmark = pytest.mark.django_db


def test_build_monitor_port(fake_app):
    assert build_monitor_port(fake_app) is None

    G(AppMetricsMonitor, port=5000, target_port=5001, app=fake_app)

    monitor_port = build_monitor_port(fake_app)
    assert monitor_port
    assert monitor_port.port == 5000
    assert monitor_port.target_port == 5001
    assert monitor_port.protocol == "TCP"
