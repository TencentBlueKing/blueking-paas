# -*- coding: utf-8 -*-
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AppMonitorConfig(AppConfig):
    name = 'paas_wl.monitoring.app_monitor'
