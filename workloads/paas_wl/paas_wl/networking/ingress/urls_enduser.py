# -*- coding: utf-8 -*-
from paas_wl.utils.basic import make_app_path, re_path

from . import views_enduser

urlpatterns = [
    re_path(
        make_app_path(r'/process_services/$'),
        views_enduser.ProcessServicesViewSet.as_view({'get': 'list'}),
        name='api.process_services',
    ),
    re_path(
        make_app_path(r'/process_services/(?P<service_name>[a-z0-9-]+)$'),
        views_enduser.ProcessServicesViewSet.as_view({'post': 'update'}),
        name='api.process_services.single',
    ),
    # Manage the default ingress rule
    re_path(
        make_app_path(r'/process_ingresses/default$'),
        views_enduser.ProcessIngressesViewSet.as_view({'post': 'update'}),
        name='api.process_ingresses.default',
    ),
]


urlpatterns += [
    re_path(
        r'applications/(?P<code>[^/]+)/domains/$',
        views_enduser.AppDomainsViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api.app_domains',
    ),
    re_path(
        r'applications/(?P<code>[^/]+)/domains/(?P<id>\d+)/$',
        views_enduser.AppDomainsViewSet.as_view({'put': 'update', 'delete': 'destroy'}),
        name='api.app_domains.singular',
    ),
]
