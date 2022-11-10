# -*- coding: utf-8 -*-
from django.urls import path

from paas_wl.workloads.images import views

urlpatterns = [
    path(
        "regions/<str:region>/apps/<str:name>/image_credentials/",
        views.AppImageCredentialsViewSet.as_view({'post': 'upsert', 'get': 'list'}),
        name="sys_api.app.image_credentials",
    ),
]
