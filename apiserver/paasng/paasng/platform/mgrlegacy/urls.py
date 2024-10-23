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

from paasng.utils.basic import make_app_pattern, re_path

from . import views

urlpatterns = [
    re_path(
        r"^api/mgrlegacy/applications/$",
        views.LegacyAppViewset.as_view({"get": "list"}),
        name="api.mgrlegacy.applications.list",
    ),
    re_path(
        make_app_pattern(r"/exposed_url_info", include_envs=False, prefix="api/mgrlegacy/applications/"),
        views.LegacyAppViewset.as_view({"get": "exposed_url_info"}),
        name="api.mgrlegacy.applications.exposed_url_info",
    ),
    # post - create migration process
    # delete - rollback - do rollback then change the entrance back
    re_path(
        r"^api/mgrlegacy/migrations/progress/$",
        views.MigrationCreateViewset.as_view({"post": "create"}),
        name="api.mgrlegacy.migrations.progress.create",
    ),
    re_path(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/state",
        views.MigrationDetailViewset.as_view({"get": "state"}),
        name="api.mgrlegacy.migrations.progress.state",
    ),
    re_path(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/old_state",
        views.MigrationDetailViewset.as_view({"get": "old_state"}),
        name="api.mgrlegacy.migrations.progress.old_state",
    ),
    # confirmed - change the entrance
    re_path(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/confirm",
        views.MigrationConfirmViewset.as_view({"post": "confirm"}),
        name="api.mgrlegacy.migrations.progress.confirm",
    ),
    re_path(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/rollback",
        views.MigrationDetailViewset.as_view({"post": "rollback"}),
        name="api.mgrlegacy.migrations.progress.rollback",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/migration/info$",
        views.ApplicationMigrationInfoAPIView.as_view({"get": "retrieve"}),
        name="api.applications.migration.info",
    ),
    # 普通应用迁移到云原生应用
    re_path(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/migrate/$",
        views.CNativeMigrationViewSet.as_view({"post": "migrate"}),
    ),
    re_path(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/rollback/$",
        views.CNativeMigrationViewSet.as_view({"post": "rollback"}),
    ),
    re_path(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/migration_processes/$",
        views.CNativeMigrationViewSet.as_view({"get": "list_processes"}),
    ),
    re_path(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/migration_processes/latest/$",
        views.CNativeMigrationViewSet.as_view({"get": "get_latest_process"}),
    ),
    re_path(
        r"^api/mgrlegacy/cloud-native/migration_processes/(?P<process_id>\d+)/$",
        views.CNativeMigrationViewSet.as_view({"get": "get_process_by_id"}),
    ),
    re_path(
        r"^api/mgrlegacy/cloud-native/migration_processes/(?P<process_id>\d+)/confirm/$",
        views.CNativeMigrationViewSet.as_view({"put": "confirm"}),
    ),
    # 普通应用进程管理
    re_path(
        make_app_pattern(r"/processes/$", prefix="api/mgrlegacy/applications/"),
        views.DefaultAppProcessViewSet.as_view({"put": "update", "get": "list"}),
    ),
    re_path(
        r"^api/mgrlegacy/applications/(?P<code>[^/]+)/entrances/$",
        views.DefaultAppEntranceViewSet.as_view({"get": "list_all_entrances"}),
    ),
    # 普通应用迁移前的 checklist 数据(如是否绑定了出口 IP 等)
    re_path(
        r"^api/mgrlegacy/applications/(?P<code>[^/]+)/checklist_info/$",
        views.RetrieveChecklistInfoViewSet.as_view({"get": "get"}),
    ),
]
