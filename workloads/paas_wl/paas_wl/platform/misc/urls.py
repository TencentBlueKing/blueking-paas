# -*- coding: utf-8 -*-
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'healthz/?$', views.HealthView.as_view(), name='api.healthz'),
    re_path(r'readyz/?$', views.ReadyzView.as_view(), name='api.readyz'),
    re_path(r'swagger(?P<format>\.json|\.yaml)$', views.schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'swagger/$', views.schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
