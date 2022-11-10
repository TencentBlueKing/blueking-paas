# -*- coding: utf-8 -*-
from typing import Optional

from paas_wl.monitoring.app_monitor import constants
from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.networking.ingress.entities.service import PServicePortPair
from paas_wl.platform.applications.models import EngineApp


def build_monitor_port(app: EngineApp) -> Optional[PServicePortPair]:
    """Generate the build-in metrics port objects"""
    try:
        monitor = AppMetricsMonitor.objects.get(app=app)
    except AppMetricsMonitor.DoesNotExist:
        return None

    return PServicePortPair(
        name=constants.METRICS_PORT_NAME,
        port=monitor.port,
        target_port=monitor.target_port,
        protocol=constants.METRICS_PORT_PROTOCOL,
    )
