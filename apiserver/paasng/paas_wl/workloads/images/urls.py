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
from django.urls import path

from . import views


# In legacy architecture, all workloads's APIs starts with a fixed prefix "/svc_workloads" and use
# a slightly different format. While the prefix is not required in the new architecture, we have
# to keep it to maintain backward-compatibility.
#
# This function helps up to build paths with the legacy prefix.
#
# TODO: Remove the 'svc_workloads' prefix and clean up the URL paths.
def make_app_pattern_legacy_wl(suffix: str) -> str:
    return r"svc_workloads/api/credentials/" + suffix


urlpatterns = [
    path(
        make_app_pattern_legacy_wl("applications/<str:code>/image_credentials/"),
        views.AppUserCredentialViewSet.as_view({"get": "list", "post": "create"}),
        name="api.applications.image_credentials",
    ),
    path(
        make_app_pattern_legacy_wl("applications/<str:code>/image_credentials/<str:name>"),
        views.AppUserCredentialViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="api.applications.image_credentials.detail",
    ),
]
