# -*- coding: utf-8 -*-
from paas_wl.utils.basic import make_app_path, re_path

from . import views_enduser

urlpatterns = [
    re_path(
        r'applications/(?P<code>[^/]+)/mres/$',
        views_enduser.MresViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='api.mres',
    ),
    re_path(
        make_app_path(r'/mres/deployments/$', include_envs=True),
        views_enduser.MresDeploymentsViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api.mres.deployments',
    ),
    re_path(
        make_app_path(r'/mres/deployments/(?P<deploy_id>[\d]+)/$'),
        views_enduser.MresDeploymentsViewSet.as_view({'get': 'retrieve'}),
        name='api.mres.deployments.singular',
    ),
    re_path(
        make_app_path(r'/mres/status/$'),
        views_enduser.MresStatusViewSet.as_view({'get': 'retrieve'}),
        name='api.mres.status',
    ),
]
