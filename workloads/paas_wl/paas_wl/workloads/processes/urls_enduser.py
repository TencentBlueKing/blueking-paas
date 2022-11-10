# -*- coding: utf-8 -*-
from paas_wl.utils.basic import make_app_path, re_path

from . import views_enduser

urlpatterns = [
    re_path(
        make_app_path(r'/processes/$'),
        views_enduser.ProcessesViewSet.as_view({'post': 'update'}),
        name='api.processes',
    ),
    re_path(
        make_app_path(r'/processes/list/$'),
        views_enduser.ListAndWatchProcsViewSet.as_view({'get': 'list'}),
        name='api.list_processes',
    ),
    re_path(
        make_app_path(r'/processes/watch/$'),
        views_enduser.ListAndWatchProcsViewSet.as_view({'get': 'watch'}),
        name='api.watch_processes',
    ),
]
