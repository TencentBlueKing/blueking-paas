# -*- coding: utf-8 -*-
import logging
from typing import TYPE_CHECKING

from paas_wl.resources.actions.exceptions import ScaleFailedException
from paas_wl.resources.utils.app import get_scheduler_client_by_app
from paas_wl.workloads.processes.managers import AppProcessManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.app import App
    from paas_wl.resources.base.client import K8sScheduler


class AppStop:
    def __init__(self, app: 'App'):
        self.app = app
        self.scheduler_client: 'K8sScheduler' = get_scheduler_client_by_app(self.app)

    def perform(self, *scale_process_names: str):
        """Apply the structure to k8s-resources

        The number of replicas of a process is defined in Model `ProcessSpec`,
        And The Command of a process is defined in `Procfile`
        """
        self.app.ensure_config()
        processes = AppProcessManager(app=self.app).assemble_processes()
        scale_processes = [p for p in processes if p.name in scale_process_names]

        try:
            self.scheduler_client.shutdown_processes(scale_processes)
        except Exception as e:
            raise ScaleFailedException(f"scale process<{scale_process_names}> for App<{self.app.name}> failed") from e
