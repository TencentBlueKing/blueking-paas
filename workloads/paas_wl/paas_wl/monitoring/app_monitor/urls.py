# -*- coding: utf-8 -*-
from django.urls import path

from paas_wl.monitoring.app_monitor import views

urlpatterns = [
    path(
        "regions/<str:region>/apps/<str:name>/metrics_monitor/",
        views.AppMetricsMonitorViewSet.as_view({'post': 'upsert', 'get': 'retrieve'}),
        name="sys_api.app.metrics_monitor",
    ),
]
