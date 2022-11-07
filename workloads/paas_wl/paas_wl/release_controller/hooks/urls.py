# -*- coding: utf-8 -*-
from django.urls import path

from paas_wl.release_controller.hooks import views

urlpatterns = [
    ###########
    # Command #
    ###########
    path(
        "regions/<str:region>/apps/<str:name>/commands/",
        views.CommandViewSet.as_view({'post': 'create'}),
    ),
    path(
        "regions/<str:region>/apps/<str:name>/commands/<uuid:uuid>",
        views.CommandViewSet.as_view({'get': 'retrieve'}),
    ),
    path(
        "regions/<str:region>/apps/<str:name>/commands/<uuid:uuid>/interruptions",
        views.CommandViewSet.as_view({'post': 'user_interrupt'}),
    ),
]
