"""
WSGI config for svc_otel project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os

from blue_krill.monitoring.prometheus.django_utils import PrometheusExposeHandler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "svc_otel.settings")

application = PrometheusExposeHandler(get_wsgi_application())
