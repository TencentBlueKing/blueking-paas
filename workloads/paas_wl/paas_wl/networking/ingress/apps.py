# -*- coding: utf-8 -*-
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class IngressConfig(AppConfig):
    name = 'paas_wl.networking.ingress'
    # Change label for backward compatibility
    label = 'services'

    def ready(self):
        from .plugins.ingress import register

        register()
