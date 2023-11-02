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

from .views import config
from .views import legacy as legacy_views
from .views import logs as logs_views

# log
urlpatterns = [
    # 结构化日志
    re_path(
        make_app_pattern(r'/log/structured/list/$'),
        logs_views.StructuredLogAPIView.as_view({"post": "query_logs"}),
        name='api.logs.structured.query_logs',
    ),
    re_path(
        make_app_pattern(r'/log/structured/date_histogram/$'),
        logs_views.StructuredLogAPIView.as_view({"post": "aggregate_date_histogram"}),
        name='api.logs.structured.aggregate_date_histogram',
    ),
    re_path(
        make_app_pattern(r'/log/structured/fields_filters/$'),
        logs_views.StructuredLogAPIView.as_view({"post": "aggregate_fields_filters"}),
        name='api.logs.structured.aggregate_fields_filters',
    ),
    # 标准输出日志
    re_path(
        make_app_pattern(r'/log/stdout/list/$'),
        logs_views.StdoutLogAPIView.as_view({"post": "query_logs_scroll"}),
        name='api.logs.stdout.query_logs',
    ),
    re_path(
        make_app_pattern(r'/log/stdout/fields_filters/$'),
        logs_views.StdoutLogAPIView.as_view({"post": "aggregate_fields_filters"}),
        name='api.logs.stdout.aggregate_fields_filters',
    ),
    # Ingress 日志
    re_path(
        make_app_pattern(r'/log/ingress/list/$'),
        logs_views.IngressLogAPIView.as_view({"post": "query_logs"}),
        name='api.logs.ingress.query_logs',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/date_histogram/$'),
        logs_views.IngressLogAPIView.as_view({"post": "aggregate_date_histogram"}),
        name='api.logs.ingress.aggregate_date_histogram',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/fields_filters/$'),
        logs_views.IngressLogAPIView.as_view({"post": "aggregate_fields_filters"}),
        name='api.logs.ingress.aggregate_fields_filters',
    ),
    # 模块维度下的日志搜索
    re_path(
        make_app_pattern(r'/log/structured/list/$', include_envs=False),
        logs_views.ModuleStructuredLogAPIView.as_view({"post": "query_logs"}),
        name='api.logs.structured.query_logs.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/structured/date_histogram/$', include_envs=False),
        logs_views.ModuleStructuredLogAPIView.as_view({"post": "aggregate_date_histogram"}),
        name='api.logs.structured.aggregate_date_histogram.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/structured/fields_filters/$', include_envs=False),
        logs_views.ModuleStructuredLogAPIView.as_view({"post": "aggregate_fields_filters"}),
        name='api.logs.structured.aggregate_fields_filters.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/stdout/list/$', include_envs=False),
        logs_views.ModuleStdoutLogAPIView.as_view({"post": "query_logs_scroll"}),
        name='api.logs.stdout.query_logs.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/stdout/fields_filters/$', include_envs=False),
        logs_views.ModuleStdoutLogAPIView.as_view({"post": "aggregate_fields_filters"}),
        name='api.logs.stdout.aggregate_fields_filters.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/list/$', include_envs=False),
        logs_views.ModuleIngressLogAPIView.as_view({"post": "query_logs"}),
        name='api.logs.ingress.query_logs.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/date_histogram/$', include_envs=False),
        logs_views.ModuleIngressLogAPIView.as_view({"post": "aggregate_date_histogram"}),
        name='api.logs.ingress.aggregate_date_histogram.legacy',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/fields_filters/$', include_envs=False),
        logs_views.ModuleIngressLogAPIView.as_view({"post": "aggregate_fields_filters"}),
        name='api.logs.ingress.aggregate_fields_filters.legacy',
    ),
    # System APIs
    url(
        r'sys/api/log/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/'
        r'envs/(?P<environment>stag|prod)/structured/list/$',
        logs_views.SysStructuredLogAPIView.as_view({"post": "query_logs"}),
        name='sys.api.logs.structured',
    ),
]

# 日志采集配置 API
urlpatterns += [
    re_path(
        make_app_pattern(r"/log/custom-collector/$", include_envs=False),
        config.CustomCollectorConfigViewSet.as_view({"get": "list", "post": "upsert"}),
    ),
    re_path(
        make_app_pattern(r"/log/custom-collector/(?P<name_en>[^/]+)/$", include_envs=False),
        config.CustomCollectorConfigViewSet.as_view({"delete": "destroy"}),
    ),
    re_path(
        make_app_pattern(r"/log/custom-collector-metadata/$", include_envs=False),
        config.CustomCollectorConfigViewSet.as_view({"get": "get_metadata"}),
    ),
]


# deprecated view
# 以下接口已注册到 APIGW, 慎重删除
urlpatterns += [
    re_path(
        make_app_pattern(r'/log/standard_output/list/$', include_envs=False),
        legacy_views.V1StdoutLogAPIView.as_view({"get": "query_logs_scroll_with_get", "post": "query_logs_scroll"}),
        name="api.logs.standard.list.deprecated",
    ),
    url(
        r'sys/api/log/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/structured/list/$',
        legacy_views.V1SysStructuredLogAPIView.as_view({"post": "query_logs", "get": "query_logs_get"}),
        name='sys.api.logs.structured.deprecated',
    ),
]
