# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ApplicationsAppConfig(AppConfig):
    name = 'paas_wl.platform.applications'
    # Change label for backward compatibility
    label = 'api'
