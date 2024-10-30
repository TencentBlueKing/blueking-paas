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

from paasng.utils.basic import re_path

from . import pluginscenter_views, views

urlpatterns = [
    # System APIs start
    re_path(
        r"^sys/api/bk_plugins/$",
        views.SysBkPluginsViewset.as_view({"get": "list"}),
        name="sys.api.bk_plugins.list",
    ),
    re_path(
        r"^sys/api/bk_plugins/(?P<code>[^/]+)/$",
        views.SysBkPluginsViewset.as_view({"get": "retrieve"}),
        name="sys.api.bk_plugins.retrieve",
    ),
    re_path(
        r"^sys/api/bk_plugins/(?P<code>[^/]+)/logs/$",
        views.SysBkPluginLogsViewset.as_view({"get": "list", "post": "list"}),
        name="sys.api.bk_plugins.logs.list",
    ),
    re_path(
        r"^sys/api/bk_plugin_tags/$",
        views.SysBkPluginTagsViewSet.as_view({"get": "list"}),
        name="sys.api.bk_plugin_tags",
    ),
    # Batch endpoints
    re_path(
        r"^sys/api/bk_plugins/batch/detailed/$",
        views.SysBkPluginsBatchViewset.as_view({"get": "list_detailed"}),
        name="sys.api.bk_plugins.list_detailed",
    ),
    # shim api for plugin-center
    re_path(
        r"^sys/api/plugins_center/bk_plugins/$",
        pluginscenter_views.PluginInstanceViewSet.as_view({"post": "create_plugin"}),
        name="sys.api.plugins_center.bk_plugins.create",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/$",
        pluginscenter_views.PluginInstanceViewSet.as_view({"put": "update_plugin", "delete": "archive_plugin"}),
        name="sys.api.plugins_center.bk_plugins.detail",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/deploy/$",
        pluginscenter_views.PluginDeployViewSet.as_view({"post": "deploy_plugin"}),
        name="sys.api.plugins_center.bk_plugins.deploy",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/deploy/(?P<deploy_id>[^/]+)/status/$",
        pluginscenter_views.PluginDeployViewSet.as_view({"get": "check_deploy_status"}),
        name="sys.api.plugins_center.bk_plugins.deploy.status",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/deploy/(?P<deploy_id>[^/]+)/logs/$",
        pluginscenter_views.PluginDeployViewSet.as_view({"get": "get_deploy_logs"}),
        name="sys.api.plugins_center.bk_plugins.deploy.logs",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/market/$",
        pluginscenter_views.PluginMarketViewSet.as_view({"post": "upsert_market_info"}),
        name="sys.api.plugins_center.bk_plugins.market.upsert",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/market/category/$",
        pluginscenter_views.PluginMarketViewSet.as_view({"get": "list_category"}),
        name="sys.api.plugins_center.bk_plugins.market.list_category",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/members/$",
        pluginscenter_views.PluginMembersViewSet.as_view({"post": "sync_members"}),
        name="sys.api.plugins_center.bk_plugins.members.sync",
    ),
    re_path(
        r"^sys/api/plugins_center/bk_plugins/(?P<code>[^/]+)/configuration/$",
        pluginscenter_views.PluginConfigurationViewSet.as_view({"post": "sync_configurations"}),
        name="sys.api.plugins_center.bk_plugins.configurations.sync",
    ),
    # System APIs end
    # User interface APIs start
    re_path(
        r"^api/bk_plugins/(?P<code>[^/]+)/profile/$",
        views.BkPluginProfileViewSet.as_view({"get": "retrieve", "patch": "patch"}),
        name="api.bk_plugins.profile",
    ),
    re_path(
        r"^api/bk_plugins/(?P<code>[^/]+)/distributors/$",
        views.DistributorRelsViewSet.as_view({"get": "list", "put": "update"}),
        name="api.bk_plugins.distributor_rels",
    ),
    re_path(
        r"^api/bk_plugin_distributors/$",
        views.DistributorsViewSet.as_view({"get": "list"}),
        name="api.bk_plugin_distributors",
    ),
    re_path(
        r"^api/bk_plugin_tags/$",
        views.BkPluginTagsViewSet.as_view({"get": "list"}),
        name="api.bk_plugin_tags",
    ),
    # User interface APIs end
]
