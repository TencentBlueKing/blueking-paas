# -*- coding: utf-8 -*-
from django.urls import path

from . import views_enduser

urlpatterns = [
    path(
        'applications/<str:code>/image_credentials/',
        views_enduser.AppUserCredentialViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='api.applications.image_credentials',
    ),
    path(
        'applications/<str:code>/image_credentials/<str:name>',
        views_enduser.AppUserCredentialViewSet.as_view({'put': 'update', 'delete': 'destroy'}),
        name='api.applications.image_credentials.detail',
    ),
]
