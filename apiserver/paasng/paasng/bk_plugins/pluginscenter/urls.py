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
from .iam_adaptor.views import PluginSelectionView

urlpatterns = [
    path(
        "api/bkplugins/filter_params/",
        views.PluginInstanceViewSet.as_view({"get": "get_filter_params"}),
    ),
    path("api/bkplugins/lists/", views.PluginInstanceViewSet.as_view({"get": "list"})),
    path("api/bkplugins/<str:pd_id>/plugins/", views.PluginInstanceViewSet.as_view({"post": "create"})),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/",
        views.PluginInstanceViewSet.as_view({"get": "retrieve", "post": "update", "delete": "destroy"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/extra_fields/",
        views.PluginInstanceViewSet.as_view({"post": "update_extra_fields"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/publisher/",
        views.PluginInstanceViewSet.as_view({"post": "update_publisher"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/visible_range/",
        views.PluginVisibleRangeViewSet.as_view({"post": "update", "get": "retrieve"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/logo/",
        views.PluginInstanceViewSet.as_view({"put": "update_logo"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/overview/",
        views.PluginInstanceViewSet.as_view({"get": "get_repo_overview"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/archive/",
        views.PluginInstanceViewSet.as_view({"post": "archive"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/reactivate/",
        views.PluginInstanceViewSet.as_view({"post": "reactivate"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/repo/commit-diff-external/"
        + "<str:from_revision>/<str:to_revision>/",
        views.PluginReleaseViewSet.as_view({"get": "get_compare_url"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/code_statistics/",
        views.PluginInstanceViewSet.as_view({"get": "get_code_submit_info"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/feature_flags/",
        views.PluginInstanceViewSet.as_view({"get": "get_feature_flags"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/",
        views.PluginReleaseViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/success/",
        views.PluginReleaseViewSet.as_view({"get": "get_success_release"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/schema/",
        views.PluginReleaseViewSet.as_view({"get": "get_release_schema"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/",
        views.PluginReleaseViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/next/",
        views.PluginReleaseViewSet.as_view({"post": "enter_next_stage"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/back/",
        views.PluginReleaseViewSet.as_view({"post": "back_to_previous_stage"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/cancel/",
        views.PluginReleaseViewSet.as_view({"post": "cancel_release"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/reset/",
        views.PluginReleaseViewSet.as_view({"post": "re_release"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/rollback/",
        views.PluginReleaseViewSet.as_view({"post": "rollback_release"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/stages/<str:stage_id>/",
        views.PluginReleaseStageViewSet.as_view({"get": "retrieve"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/stages/<str:stage_id>/rerun/",
        views.PluginReleaseStageViewSet.as_view({"post": "rerun"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/stages/<str:stage_id>/status/",
        views.PluginReleaseStageViewSet.as_view({"post": "update_stage_status"}),
    ),
    # 灰度发布策略
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/releases/<str:release_id>/strategy/",
        views.PluginReleaseStrategyViewSet.as_view({"get": "list", "post": "update"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/market/",
        views.PluginMarketViewSet.as_view({"get": "retrieve", "post": "upsert"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/logs/standard_output/",
        views.PluginLogViewSet.as_view({"post": "query_standard_output_logs"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/logs/structure_logs/",
        views.PluginLogViewSet.as_view({"post": "query_structure_logs"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/logs/ingress_logs/",
        views.PluginLogViewSet.as_view({"post": "query_ingress_logs"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/logs/aggregate_date_histogram/<str:log_type>/",
        views.PluginLogViewSet.as_view({"post": "aggregate_date_histogram"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/logs/aggregate_fields_filters/<str:log_type>/",
        views.PluginLogViewSet.as_view({"post": "aggregate_fields_filters"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/members/",
        views.PluginMembersViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/members/leave/",
        views.PluginMembersViewSet.as_view({"post": "leave"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/members/<str:username>/",
        views.PluginMembersViewSet.as_view({"delete": "destroy", "put": "update_role"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/configurations/",
        views.PluginConfigViewSet.as_view({"get": "list", "post": "upsert"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/configurations/<str:config_id>/",
        views.PluginConfigViewSet.as_view({"delete": "destroy"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/members/leave/",
        views.PluginMembersViewSet.as_view({"post": "leave"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/members/<str:username>/",
        views.PluginMembersViewSet.as_view({"delete": "destroy"}),
    ),
    path(
        "api/bkplugins/<str:pd_id>/plugins/<str:plugin_id>/operations/",
        views.OperationRecordViewSet.as_view({"get": "list"}),
    ),
    path(
        "api/bkplugins/plugin_definitions/schemas/",
        views.SchemaViewSet.as_view({"get": "get_plugins_schema"}),
    ),
    path(
        "api/bkplugins/plugin_definitions/<str:pd_id>/market_schema/",
        views.SchemaViewSet.as_view({"get": "get_market_schema"}),
    ),
    path(
        "api/bkplugins/plugin_definitions/<str:pd_id>/basic_info_schema/",
        views.SchemaViewSet.as_view({"get": "get_basic_info_schema"}),
    ),
    path(
        "api/bkplugins/plugin_definitions/<str:pd_id>/configuration_schema/",
        views.SchemaViewSet.as_view({"get": "get_config_schema"}),
    ),
    # iam selection api
    path(
        "api/bkplugins/shim/iam/selection/plugin_view/",
        PluginSelectionView.as_view(),
    ),
]
