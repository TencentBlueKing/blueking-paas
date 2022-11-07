# -*- coding: utf-8 -*-
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ProcessesConfig(AppConfig):
    name = 'paas_wl.workloads.processes'

    def ready(self):
        # Run initialization jobs
        from .models import initialize_default_proc_spec_plans

        try:
            initialize_default_proc_spec_plans()
        except Exception as e:
            logger.warning('Can not initialize process spec plans: %s', e)
