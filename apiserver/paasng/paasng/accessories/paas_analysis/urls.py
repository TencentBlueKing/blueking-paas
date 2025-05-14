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

RE_METRIC_SOURCE_TYPE = "(?P<metric_source_type>ingress|user_tracker)"
RE_DIMENSION_TYPE = "(?P<dimension>path|user)"

urlpatterns = [
    re_path(
        make_app_pattern(f"/analysis/m/{RE_METRIC_SOURCE_TYPE}/config", include_envs=True),
        views.PageViewConfigViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.config",
    ),
    re_path(
        make_app_pattern(f"/analysis/m/{RE_METRIC_SOURCE_TYPE}/metrics/aggregate_by_interval$", include_envs=True),
        views.PageViewMetricTrendViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.aggregate_by_interval$",
    ),
    re_path(
        make_app_pattern(f"/analysis/m/{RE_METRIC_SOURCE_TYPE}/metrics/total$", include_envs=True),
        views.PageViewTotalMetricsViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.total",
    ),
    re_path(
        make_app_pattern(
            f"/analysis/m/{RE_METRIC_SOURCE_TYPE}/metrics/dimension/{RE_DIMENSION_TYPE}$",
            include_envs=True,
        ),
        views.DimensionMetricsViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.group_by_dimension",
    ),
    # 自定义事件
    re_path(
        make_app_pattern("/analysis/event/config", include_envs=True),
        views.CustomEventConfigViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.event.config",
    ),
    re_path(
        make_app_pattern("/analysis/event/metrics/total$", include_envs=True),
        views.CustomEventTotalMetricsViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.event.total",
    ),
    re_path(
        make_app_pattern("/analysis/event/metrics/overview", include_envs=True),
        views.CustomEventOverviewViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.event.overview",
    ),
    re_path(
        make_app_pattern(
            "/analysis/event/metrics/c/(?P<category>[^/]+)/d/(?P<dimension>[^/]+)/detail", include_envs=True
        ),
        views.CustomEventDetailViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.event.detail",
    ),
    re_path(
        make_app_pattern("/analysis/event/metrics/aggregate_by_interval", include_envs=True),
        views.CustomEventTrendViewSet.as_view({"get": "retrieve"}),
        name="api.analysis.metrics.event.aggregate_by_interval",
    ),
    # 自定义站点
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/config$",
        views.PageViewConfigViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.config",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/metrics/aggregate_by_interval$",
        views.PageViewMetricTrendViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.aggregate_by_interval$",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/metrics/total$",
        views.PageViewTotalMetricsViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.total",
    ),
    re_path(
        f"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/metrics/dimension/{RE_DIMENSION_TYPE}$",  # noqa
        views.DimensionMetricsViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.group_by_dimension",
    ),
    # 自定义站点-自定义事件
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/event/config$",
        views.CustomEventConfigViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.event.config",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/event/metrics/total$",
        views.CustomEventTotalMetricsViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.event.total",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/event/metrics/overview",
        views.CustomEventOverviewViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.event.overview",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/event/metrics/c/(?P<category>[^/]+)/d/(?P<dimension>[^/]+)/detail",  # noqa
        views.CustomEventDetailViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.event.detail",
    ),
    re_path(
        r"^api/bkapps/applications/(?P<code>[^/]+)/analysis/site/(?P<site_name>default)/event/metrics/aggregate_by_interval",  # noqa
        views.CustomEventTrendViewSet.as_view({"get": "retrieve_for_custom_site"}),
        name="api.analysis.custom_site.metrics.event.aggregate_by_interval",
    ),
    # ingress related endpoints
    re_path(
        make_app_pattern(
            "/analysis/ingress/tracking_status/$",
            include_envs=False,
        ),
        views.IngressConfigViewSet.as_view({"post": "update_tracking_status", "get": "get_tracking_status"}),
        name="api.analysis.ingress.tracking_status",
    ),
]
