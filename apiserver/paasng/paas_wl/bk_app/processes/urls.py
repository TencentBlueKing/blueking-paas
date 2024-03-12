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
from functools import partial

from paasng.utils.basic import make_app_pattern, re_path

from . import views

# In legacy architecture, all workloads's APIs starts with a fixed prefix "/svc_workloads" and use
# a slightly different format. While the prefix is not required in the new architecture, we have
# to keep it to maintain backward-compatibility.
#
# This function helps up to build paths with the legacy prefix.
#
# TODO: Remove the 'svc_workloads' prefix and clean up the URL paths.
make_app_pattern_legacy_wl = partial(make_app_pattern, prefix="svc_workloads/api/processes/applications/")

urlpatterns = [
    re_path(
        make_app_pattern(r"/processes/$"),
        views.ProcessesViewSet.as_view({"post": "update"}),
        name="api.processes.update",
    ),
    # Cloud-native type application
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/envs/(?P<environment>stag|prod)/processes/list/$",
        views.CNativeListAndWatchProcsViewSet.as_view({"get": "list"}),
        name="api.list_processes.namespace_scoped",
    ),
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/envs/(?P<environment>stag|prod)/processes/watch/$",
        views.CNativeListAndWatchProcsViewSet.as_view({"get": "watch"}),
        name="api.watch_processes.namespace_scoped",
    ),
    # Below paths using legacy prefix.
    #
    # TODO: This path a duplication with "api.processes.update", should be removed in the future.
    re_path(
        make_app_pattern_legacy_wl(r"/processes/$"),
        views.ProcessesViewSet.as_view({"post": "update"}),
        name="api.processes",
    ),
    # Default type application
    re_path(
        make_app_pattern_legacy_wl(r"/processes/list/$"),
        views.ListAndWatchProcsViewSet.as_view({"get": "list"}),
        name="api.list_processes",
    ),
    re_path(
        make_app_pattern_legacy_wl(r"/processes/watch/$"),
        views.ListAndWatchProcsViewSet.as_view({"get": "watch"}),
        name="api.watch_processes",
    ),
]
