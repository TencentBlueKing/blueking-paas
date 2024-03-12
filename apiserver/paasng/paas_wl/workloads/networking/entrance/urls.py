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
from paasng.utils.basic import re_path

from . import views


# In legacy architecture, all workloads's APIs starts with a fixed prefix "/svc_workloads" and use
# a slightly different format. While the prefix is not required in the new architecture, we have
# to keep it to maintain backward-compatibility.
#
# This function helps up to build paths with the legacy prefix.
#
# TODO: Remove the 'svc_workloads' prefix and clean up the URL paths.
def make_app_pattern_legacy_wl(suffix: str) -> str:
    return r"^svc_workloads/api/services/" + suffix


urlpatterns = [
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/domains/$",
        views.AppDomainsViewSet.as_view({"get": "list", "post": "create"}),
        name="api.app_domains",
    ),
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/domains/(?P<id>\d+)/$",
        views.AppDomainsViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="api.app_domains.singular",
    ),
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/domains/configs/$",
        views.AppDomainsViewSet.as_view({"get": "list_configs"}),
        name="api.app_domains.configs",
    ),
    # Entrance related paths
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/entrances/$",
        views.AppEntranceViewSet.as_view({"get": "list_all_entrances"}),
        name="api.applications.entrances.all_entrances",
    ),
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/entrances/$",
        views.AppEntranceViewSet.as_view({"get": "list_module_available_entrances"}),
        name="api.applications.entrances.all_module_entrances",
    ),
    # TODO: These paths are duplicated an exists only because backward-compatibility, remove
    # them in the future.
    re_path(
        make_app_pattern_legacy_wl(r"applications/(?P<code>[^/]+)/domains/$"),
        views.AppDomainsViewSet.as_view({"get": "list", "post": "create"}),
        name="api.app_domains",
    ),
    re_path(
        make_app_pattern_legacy_wl(r"applications/(?P<code>[^/]+)/domains/(?P<id>\d+)/$"),
        views.AppDomainsViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="api.app_domains.singular",
    ),
    re_path(
        make_app_pattern_legacy_wl(r"applications/(?P<code>[^/]+)/domains/configs/$"),
        views.AppDomainsViewSet.as_view({"get": "list_configs"}),
        name="api.app_domains.configs",
    ),
    # Deprecated: use `api.app_domains.configs` instead
    # TODO: Remove this path.
    re_path(
        "^api/bkapps/applications/(?P<code>[^/]+)/custom_domains/config/$",
        views.AppDomainsViewSet.as_view({"get": "list_configs"}),
        name="api.custom_domains_config",
    ),
]
