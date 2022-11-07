# -*- coding: utf-8 -*-

from __future__ import absolute_import

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paas_wl.settings")

from celery import Celery

app = Celery('paas_wl')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
