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
from django.conf.urls import url

from paasng.utils.basic import make_app_pattern, re_path

from . import views

urlpatterns = [
    re_path(
        make_app_pattern(r"/mres/revisions/(?P<revision_id>[\d]+)/$"),
        views.MresVersionViewSet.as_view({"get": "retrieve"}),
        name="api.mres.revision.singular",
    ),
    re_path(
        make_app_pattern(r"/mres/image_tags/$", include_envs=False),
        views.ImageRepositoryView.as_view({"get": "list_tags"}),
        name="api.mres.image_tags.list",
    ),
    re_path(
        r"api/mres/quota_plans/$",
        views.ResQuotaPlanOptionsView.as_view(),
    ),
    re_path(
        make_app_pattern(r"/mres/volume_mounts/$", include_envs=False),
        views.VolumeMountViewSet.as_view({"get": "list", "post": "create"}),
        name="api.mres.volume_mount",
    ),
    re_path(
        make_app_pattern(r"/mres/volume_mounts/(?P<mount_id>\w+)/$", include_envs=False),
        views.VolumeMountViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="api.mres.volume_mount.detail",
    ),
    url(
        r"api/bkapps/applications/(?P<code>[^/]+)/mres/mount_sources/$",
        views.MountSourceViewSet.as_view({"get": "list", "post": "create", "delete": "destroy", "put": "update"}),
        name="api.mres.mount_source",
    ),
    url(
        r"api/bkapps/applications/(?P<code>[^/]+)/mres/storage_class/$",
        views.StorageClassViewSet.as_view({"get": "check"}),
        name="api.mres.storage_class",
    ),
]
