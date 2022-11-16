# -*- coding: utf-8 -*-
"""Archive related deploy functions"""
import logging
from typing import Optional

from paas_wl.monitoring.app_monitor.managers import make_bk_monitor_controller
from paas_wl.platform.applications.models.app import EngineApp
from paas_wl.platform.applications.struct_models import get_env_by_engine_app_id
from paas_wl.workloads.processes.controllers import get_proc_mgr

logger = logging.getLogger(__name__)


class ArchiveOperationController:
    """Controller for offline operation"""

    def __init__(self, engine_app: EngineApp, operation_id: Optional[str] = None):
        self.operation_id = operation_id
        self.engine_app: EngineApp = engine_app

    def start(self):
        self.stop_all_processes()
        make_bk_monitor_controller(self.engine_app).remove()

    def stop_all_processes(self):
        """Stop all processes"""
        ctl = get_proc_mgr(get_env_by_engine_app_id(self.engine_app.pk))
        for spec in self.engine_app.process_specs.all():
            ctl.stop(proc_type=spec.name)
