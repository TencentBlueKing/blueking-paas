# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from paasng.plat_mgt.applications import views
from paasng.utils.basic import re_path

urlpatterns = [
    # 平台管理 - 应用列表
    re_path(
        r"^api/plat_mgt/applications/$",
        views.ApplicationListViewSet.as_view({"get": "list"}),
        name="plat_mgt.applications.list_applications",
    ),
    re_path(
        r"^api/plat_mgt/applications/tenant_app_statistics/$",
        views.ApplicationListViewSet.as_view({"get": "list_tenant_app_statistics"}),
        name="plat_mgt.applications.list_tenant_app_statistics",
    ),
    re_path(
        r"^api/plat_mgt/applications/tenant_mode_list/$",
        views.ApplicationListViewSet.as_view({"get": "list_tenant_modes"}),
        name="plat_mgt.applications.list_tenant_modes",
    ),
    re_path(
        r"^api/plat_mgt/applications/types/$",
        views.ApplicationListViewSet.as_view({"get": "list_app_types"}),
        name="plat_mgt.applications.types",
    ),
    # 平台管理 - 应用详情
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/$",
        views.ApplicationDetailViewSet.as_view({"get": "retrieve", "post": "update_app_name"}),
        name="plat_mgt.applications.retrieve_app_name",
    ),
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/modules/(?P<module_name>[^/]+)/envs/(?P<env_name>[^/]+)/cluster/$",
        views.ApplicationDetailViewSet.as_view({"post": "update_cluster"}),
        name="plat_mgt.applications.update_cluster",
    ),
    re_path(
        r"^api/plat_mgt/clusters/$",
        views.ApplicationDetailViewSet.as_view({"get": "list_clusters"}),
        name="plat_mgt.applications.list_clusters",
    ),
    # 平台管理 - 应用特性
    re_path(
        r"^api/plat_mgt/applications/(?P<app_code>[^/]+)/feature_flags/$",
        views.ApplicationFeatureViewSet.as_view({"get": "list", "put": "update"}),
        name="plat_mgt.applications.feature_flags",
    ),
]
