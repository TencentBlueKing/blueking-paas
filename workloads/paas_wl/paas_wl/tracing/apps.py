# -*- coding: utf-8 -*-
from celery.signals import worker_process_init
from django.apps import AppConfig

from .setup import setup_by_settings


class TracingConfig(AppConfig):
    name = 'paas_wl.tracing'

    def ready(self):
        setup_by_settings()


@worker_process_init.connect(weak=False)
def worker_process_init_otel_trace_setup(*args, **kwargs):
    setup_by_settings()
