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
    url(
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
    url(
        r"^api/mgrlegacy/migrations/progress/$",
        views.MigrationCreateViewset.as_view({"post": "create"}),
        name="api.mgrlegacy.migrations.progress.create",
    ),
    url(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/state",
        views.MigrationDetailViewset.as_view({"get": "state"}),
        name="api.mgrlegacy.migrations.progress.state",
    ),
    url(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/old_state",
        views.MigrationDetailViewset.as_view({"get": "old_state"}),
        name="api.mgrlegacy.migrations.progress.old_state",
    ),
    # confirmed - change the entrance
    url(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/confirm",
        views.MigrationConfirmViewset.as_view({"post": "confirm"}),
        name="api.mgrlegacy.migrations.progress.confirm",
    ),
    # just for local debug
    url(
        r"^api/mgrlegacy/migrations/progress/records/",
        views.MigrationDetailViewset.as_view({"get": "list"}),
        name="api.mgrlegacy.migrations.progress.records",
    ),
    url(
        r"^api/mgrlegacy/migrations/progress/(?P<id>\d+)/rollback",
        views.MigrationDetailViewset.as_view({"post": "rollback"}),
        name="api.mgrlegacy.migrations.progress.rollback",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/migration/info$",
        views.ApplicationMigrationInfoAPIView.as_view({"get": "retrieve"}),
        name="api.applications.migration.info",
    ),
    # 普通应用迁移到云原生应用
    url(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/migrate/$",
        views.CNativeMigrationViewSet.as_view({"post": "migrate"}),
    ),
    url(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/rollback/$",
        views.CNativeMigrationViewSet.as_view({"post": "rollback"}),
    ),
    url(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/migration_processes/$",
        views.CNativeMigrationViewSet.as_view({"get": "list_processes"}),
    ),
    url(
        r"^api/mgrlegacy/cloud-native/applications/(?P<code>[^/]+)/migration_processes/latest/$",
        views.CNativeMigrationViewSet.as_view({"get": "get_latest_process"}),
    ),
    url(
        r"^api/mgrlegacy/cloud-native/migration_processes/(?P<process_id>\d+)/$",
        views.CNativeMigrationViewSet.as_view({"get": "get_process_by_id"}),
    ),
    url(
        r"^api/mgrlegacy/cloud-native/migration_processes/(?P<process_id>\d+)/confirm/$",
        views.CNativeMigrationViewSet.as_view({"put": "confirm"}),
    ),
    # 普通应用进程管理
    re_path(
        make_app_pattern(r"/processes/list/$", prefix="api/mgrlegacy/applications/"),
        views.DefaultAppProcessViewSet.as_view({"get": "list"}),
    ),
    re_path(
        make_app_pattern(r"/processes/$", prefix="api/mgrlegacy/applications/"),
        views.DefaultAppProcessViewSet.as_view({"post": "update"}),
    ),
]
