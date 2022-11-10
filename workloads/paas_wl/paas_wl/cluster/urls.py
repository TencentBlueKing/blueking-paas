# -*- coding: utf-8 -*-
from django.urls import re_path

from paas_wl.utils import text

from . import views

urlpatterns = [
    re_path(r"^regions/%s/clusters/$" % (text.PVAR_REGION,), views.RegionClustersViewSet.as_view({'get': 'list'})),
    re_path(r"^regions/%s/settings/$" % (text.PVAR_REGION,), views.RegionSettingsViewSet.as_view({'get': 'retrieve'})),
]
