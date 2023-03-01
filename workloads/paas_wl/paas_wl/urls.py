# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""Root URLs
"""
from django.urls import include, re_path

urlpatterns = [
    re_path(r'', include('paas_wl.metrics.urls')),
    re_path(r'^', include('paas_wl.platform.system_api.urls')),
    re_path(r'^', include('paas_wl.platform.misc.urls')),
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
