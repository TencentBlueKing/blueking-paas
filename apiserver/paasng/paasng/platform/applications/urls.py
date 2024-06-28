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

from django.conf.urls import url

from paasng.infras.accounts.views import OauthTokenViewSet

from . import views

urlpatterns = [
    # Every API startswith '/api/bkapps', 'bkapps' refers to blueking applications namespace
    url(
        r"^api/bkapps/applications/v2/$",
        views.ApplicationCreateViewSet.as_view({"post": "create_v2"}),
        name="api.applications.create_v2",
    ),
    url(
        r"^api/bkapps/third-party/$",
        views.ApplicationCreateViewSet.as_view({"post": "create_third_party"}),
        name="api.applications.create.third_party",
    ),
    url(
        r"^api/bkapps/cloud-native/$",
        views.ApplicationCreateViewSet.as_view({"post": "create_cloud_native"}),
        name="api.applications.create.cloud_native",
    ),
    url(
        r"^api/bkapps/applications/creation/options/$",
        views.ApplicationCreateViewSet.as_view({"get": "get_creation_options"}),
        name="api.applications.creation.options",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/$",
        views.ApplicationViewSet.as_view({"get": "retrieve", "delete": "destroy", "put": "update"}),
        name="api.applications.detail",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/logo/$",
        views.ApplicationLogoViewSet.as_view({"get": "retrieve", "put": "update"}),
        name="api.applications.logo",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/secret_verifications/$",
        views.ApplicationExtraInfoViewSet.as_view({"post": "get_secret"}),
        name="api.applications.detail.secret",
    ),
    url(
        r"^api/bkapps/applications/lists/detailed$",
        views.ApplicationViewSet.as_view({"get": "list_detailed"}),
        name="api.applications.lists.detailed",
    ),
    url(
        r"^api/bkapps/applications/lists/minimal$",
        views.ApplicationViewSet.as_view({"get": "list_minimal"}),
        name="api.applications.lists.minimal",
    ),
    url(
        r"^api/bkapps/applications/lists/search$",
        views.ApplicationViewSet.as_view({"get": "list_search"}),
        name="api.applications.lists.search",
    ),
    url(
        r"^api/bkapps/applications/lists/idle/$",
        views.ApplicationViewSet.as_view({"get": "list_idle"}),
        name="api.applications.lists.idle",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/overview/$",
        views.ApplicationViewSet.as_view({"get": "get_overview"}),
        name="api.applications.overview",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/members/$",
        views.ApplicationMembersViewSet.as_view({"get": "list", "post": "create"}),
        name="api.applications.members",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/members/(?P<user_id>[0-9a-z]+)/?$",
        views.ApplicationMembersViewSet.as_view({"delete": "destroy", "put": "update"}),
        name="api.applications.members.detail",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/leave/?$",
        views.ApplicationMembersViewSet.as_view({"post": "leave"}),
        name="api.applications.members.leave",
    ),
    url(
        r"^api/bkapps/applications/members/roles/$",
        views.ApplicationMembersViewSet.as_view({"get": "get_roles"}),
        name="api.applications.members.get_roles",
    ),
]


# 标记
urlpatterns += [
    url(
        r"^api/bkapps/accounts/marked_applications/(?P<code>[^/]+)/$",
        views.ApplicationMarkedViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="api.user.mark.applications.detail",
    ),
    url(
        r"^api/bkapps/accounts/marked_applications/$",
        views.ApplicationMarkedViewSet.as_view({"get": "list", "post": "create"}),
        name="api.user.mark.applications",
    ),
]


# 统计相关
urlpatterns += [
    url(
        r"^api/bkapps/applications/statistics/group_by_state/$",
        views.ApplicationGroupByStateStatisticsView.as_view(),
        name="api.applications.statistics.group_by_state",
    ),
    url(
        r"^api/bkapps/applications/summary/group_by_field/$",
        views.ApplicationGroupByFieldStatisticsView.as_view(),
        name="api.applications.statistics.group_by_field",
    ),
]

# 功能开关 与 资源保护
urlpatterns += [
    url(
        r"^api/bkapps/applications/feature_flags/(?P<code>[^/]+)/$",
        views.ApplicationFeatureFlagViewSet.as_view({"get": "list"}),
        name="api.applications.feature_flags.list",
    ),
    url(
        r"^api/bkapps/applications/feature_flags/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/env/(?P<environment>[^/]+)/$",
        views.ApplicationFeatureFlagViewSet.as_view({"get": "list_with_env"}),
        name="api.applications.feature_flags.list_with_env",
    ),
    url(
        r"^api/bkapps/applications/feature_flags/(?P<code>[^/]+)/switch/app_desc_flag/$",
        views.ApplicationFeatureFlagViewSet.as_view({"put": "switch_app_desc_flag"}),
        name="api.applications.feature_flags.switch.app_desc_flag",
    ),
    url(
        r"^api/bkapps/applications/(?P<code>[^/]+)/protections/$",
        views.ApplicationResProtectionsViewSet.as_view({"get": "list"}),
        name="api.applications.protections",
    ),
]

# 签发应用 AccessToken

urlpatterns += [
    url(
        r"^api/bkapps/applications/(?P<app_code>[^/]+)/oauth/token/(?P<env_name>test|prod|lesscode)/$",
        OauthTokenViewSet.as_view({"get": "fetch_app_token"}),
        name="api.applications.oauth.token",
    ),
    url(
        r"^api/bkapps/applications/(?P<app_code>[^/]+)/oauth/token/(?P<env_name>test|prod|lesscode)/refresh$",
        OauthTokenViewSet.as_view({"post": "refresh_app_token"}),
        name="api.applications.oauth.token.refresh",
    ),
    url(
        r"^api/bkapps/applications/(?P<app_code>[^/]+)/oauth/token/(?P<env_name>test|prod|lesscode)/validate$",
        OauthTokenViewSet.as_view({"post": "validate_app_token"}),
        name="api.applications.oauth.token.validate",
    ),
]

# 轻应用
urlpatterns += [
    url(
        "^sys/api/light-applications/$",
        views.LightAppViewSet.as_view({"post": "create", "delete": "delete", "patch": "edit", "get": "query"}),
        name="sys.api.light-applications",
    ),
]


# 注册在 APIGW 网关上的 API, 输入、输出参数不能变更需走运营侧变更流程
urlpatterns += [
    url(
        r"^apigw/api/bkapps/applications/$",
        views.ApplicationCreateViewSet.as_view({"post": "create_lesscode_app"}),
        name="api.applications.apigw.create_lesscode_app",
    ),
    # 系统 API，给固定的系统使用
    url(
        r"^sys/api/bkapps/(?P<sys_id>[^/]+)/third_app/$",
        views.SysAppViewSet.as_view({"post": "create_sys_third_app"}),
        name="sys.applications.create_third_app.sys",
    ),
]

# Multi-editions specific start

try:
    from .urls_ext import urlpatterns as urlpatterns_ext

    urlpatterns += urlpatterns_ext
except ImportError:
    pass

# Multi-editions specific end
