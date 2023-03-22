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

# log
urlpatterns = [
    # 结构化日志
    re_path(
        make_app_pattern(r'/log/structured/list/$'),
        views.StructuredLogAPIView.as_view({"get": "query_logs", "post": "query_logs"}),
        name='api.logs.structured.query_logs',
    ),
    re_path(
        make_app_pattern(r'/log/structured/date_histogram/$'),
        views.StructuredLogAPIView.as_view({"get": "aggregate_date_histogram", "post": "aggregate_date_histogram"}),
        name='api.logs.structured.aggregate_date_histogram',
    ),
    re_path(
        make_app_pattern(r'/log/structured/fields_filters/$'),
        views.StructuredLogAPIView.as_view({"get": "aggregate_fields_filters", "post": "aggregate_fields_filters"}),
        name='api.logs.structured.aggregate_fields_filters',
    ),
    # 标准输出日志
    re_path(
        make_app_pattern(r'/log/stdout/list/$'),
        views.StdoutLogAPIView.as_view({"get": "query_logs", "post": "query_logs"}),
        name='api.logs.stdout.query_logs',
    ),
    # re_path(
    #     make_app_pattern(r'/log/stdout/date_histogram/$', include_envs=False),
    #     views.StdoutLogAPIView.as_view({"get": "aggregate_date_histogram", "post": "aggregate_date_histogram"}),
    #     name='api.logs.stdout.aggregate_date_histogram',
    # ),
    # re_path(
    #     make_app_pattern(r'/log/stdout/fields_filters/$', include_envs=False),
    #     views.StdoutLogAPIView.as_view({"get": "aggregate_fields_filters", "post": "aggregate_fields_filters"}),
    #     name='api.logs.stdout.aggregate_fields_filters',
    # ),
    # Ingress 日志
    re_path(
        make_app_pattern(r'/log/ingress/list/$'),
        views.IngressLogAPIView.as_view({"get": "query_logs", "post": "query_logs"}),
        name='api.logs.ingress.query_logs',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/date_histogram/$'),
        views.IngressLogAPIView.as_view({"get": "aggregate_date_histogram", "post": "aggregate_date_histogram"}),
        name='api.logs.ingress.aggregate_date_histogram',
    ),
    re_path(
        make_app_pattern(r'/log/ingress/fields_filters/$'),
        views.IngressLogAPIView.as_view({"get": "aggregate_fields_filters", "post": "aggregate_fields_filters"}),
        name='api.logs.ingress.aggregate_fields_filters',
    ),
    # System APIs
    url(
        r'sys/api/log/applications/(?P<code>[^/]+)/modules/(?P<module_name>[^/]+)/'
        r'envs/(?P<environment>stag|prod)/structured/list/$',
        views.SysStructuredLogAPIView.as_view({"get": "query_logs", "post": "query_logs"}),
        name='sys.api.logs.structured',
    ),
]
