# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

try:
    # prometheus 多进程时, metrics 存放的文件夹
    os.environ.setdefault("prometheus_multiproc_dir", "prometheus")
    path = os.environ.get('prometheus_multiproc_dir')
    if path is not None:
        os.mkdir(path)
except Exception:
    pass

__all__ = ['celery_app']
