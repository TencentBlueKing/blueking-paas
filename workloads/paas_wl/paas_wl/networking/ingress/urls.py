# -*- coding: utf-8 -*-
from django.urls import re_path

from paas_wl.utils import text

from . import views

PVAR_SERVICE_NAME = '(?P<service_name>[a-z0-9-]+)'

urlpatterns = [
    # Manage the default ingress rule
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/proc_ingresses/actions/sync$',
        views.ProcIngressViewSet.as_view({'post': 'sync'}),
    ),
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/domains/$',
        views.AppDomainViewSet.as_view({'get': 'list', 'put': 'update'}),
    ),
    re_path(
        '^applications/(?P<code>[^/]+)/custom_domains/$',
        views.AppCustomDomainViewSet.as_view({'get': 'list'}),
    ),
    # Shared certificates
    re_path(
        '^app_certs/shared/$',
        views.AppDomainSharedCertsViewSet.as_view({'post': 'create', 'get': 'list'}),
    ),
    re_path(
        '^app_certs/shared/(?P<name>[a-zA-Z0-9_-]+)$',
        views.AppDomainSharedCertsViewSet.as_view({'get': 'retrieve', 'post': 'update', 'delete': 'destroy'}),
    ),
    # Subpath
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/subpaths/$',
        views.AppSubpathViewSet.as_view({'get': 'list', 'put': 'update'}),
    ),
]
