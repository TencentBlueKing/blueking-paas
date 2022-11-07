# -*- coding: utf-8 -*-
from django.apps import AppConfig


class EgressAppConfig(AppConfig):
    name = 'paas_wl.networking.egress'
    # Change label for backward compatibility
    label = 'region'
