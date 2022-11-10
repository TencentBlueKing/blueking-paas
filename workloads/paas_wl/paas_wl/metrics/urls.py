# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import ExportToDjangoView

urlpatterns = [url(r"^metrics$", ExportToDjangoView.as_view(), name="prometheus-django-metrics")]
