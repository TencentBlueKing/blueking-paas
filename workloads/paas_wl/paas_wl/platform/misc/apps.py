# -*- coding: utf-8 -*-
from django.apps import AppConfig

from .utils import init_sentry_sdk


class MiscAppConfig(AppConfig):
    name = 'paas_wl.platform.misc'

    def ready(self):
        init_sentry_sdk()
