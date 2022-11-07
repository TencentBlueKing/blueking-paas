# -*- coding: utf-8 -*-
"""Root URLs
"""
from django.urls import include, re_path

urlpatterns = [
    re_path(r'', include('paas_wl.metrics.urls')),
    re_path(r'^', include('paas_wl.platform.system_api.urls')),
    re_path(r'^', include('paas_wl.platform.misc.urls')),
    re_path(r'^', include('paas_wl.cluster.urls')),
    re_path(r'^', include('paas_wl.networking.egress.urls')),
    re_path(r'^services/', include('paas_wl.networking.ingress.urls')),
    re_path(r'', include('paas_wl.release_controller.hooks.urls')),
    re_path(r'', include('paas_wl.workloads.images.urls')),
    re_path(r"", include("paas_wl.admin.urls")),
    re_path(r"", include("paas_wl.monitoring.app_monitor.urls")),
    re_path('', include("paas_wl.cnative.specs.urls")),
]

# Layer: provide service for end users directly

urlpatterns += [
    # Rename "region" to "scheduling" in path because "scheduling" is a better at describing
    # endpoints related with cluster's egress infos and etc.
    re_path(r'^api/scheduling/', include('paas_wl.networking.egress.urls_enduser')),
    re_path(r'^api/services/', include('paas_wl.networking.ingress.urls_enduser')),
    re_path(r'^api/processes/', include('paas_wl.workloads.processes.urls_enduser')),
    re_path(r'^api/cnative/specs/', include('paas_wl.cnative.specs.urls_enduser')),
    re_path(r'^api/credentials/', include('paas_wl.workloads.images.urls_enduser')),
]
