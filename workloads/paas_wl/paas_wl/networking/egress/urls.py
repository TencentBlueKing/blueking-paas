# -*- coding: utf-8 -*-
from django.urls import re_path

from paas_wl.utils import text

from . import views

urlpatterns = [
    re_path(
        f'^regions/{text.PVAR_REGION}/apps/{text.PVAR_NAME}/rcstate_binding/$',
        views.RCStateBindingsViewSet.as_view({'post': 'create', 'delete': 'destroy'}),
    ),
    re_path(
        # use 'services/' prefix to be backward-compatible
        f'^(services/)?regions/{text.PVAR_REGION}/clusters/{text.PVAR_CLUSTER_NAME}/egress_info/$',
        views.ClusterEgressViewSet.as_view({'get': 'retrieve'}),
    ),
]
