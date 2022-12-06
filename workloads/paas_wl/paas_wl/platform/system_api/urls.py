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
"""Root URLs
"""
from django.urls import include, re_path
from rest_framework.routers import DefaultRouter

from paas_wl.utils.basic import make_app_path

from . import views

router = DefaultRouter(trailing_slash=False)


PVAR_REGION = '(?P<region>[a-z0-9_-]{1,32})'
PVAR_NAME = '(?P<name>[a-z0-9_-]{1,64})'
# 32/36: with or without "-"
PVAR_UUID = '(?P<uuid>[0-9a-f-]{32,36})'
PVAR_PROCESS_INSTANCE_NAME = '(?P<process_instance_name>[.a-z0-9_-]+)'
PVAR_PROCESS_TYPE = '(?P<process_type>[a-z0-9-]+)'


urlpatterns = [
    re_path(r'^', include(router.urls)),
    re_path(
        r"^regions/%s/apps/%s/?$" % (PVAR_REGION, PVAR_NAME),
        views.AppViewSet.as_view({'get': 'retrieve', 'post': 'update', 'delete': 'destroy'}),
    ),
    re_path(r"^regions/%s/apps/$" % PVAR_REGION, views.AppViewSet.as_view({'get': 'list', 'post': 'create'})),
    # App Scale
    re_path(
        r"^regions/%s/apps/%s/processes/$" % (PVAR_REGION, PVAR_NAME),
        views.ProcessViewSet.as_view({'get': 'list_processes_statuses'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/processes/specs/$" % (PVAR_REGION, PVAR_NAME),
        views.ProcessViewSet.as_view({'get': 'list_processes_specs', 'post': 'sync_specs'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/processes/%s/instances/%s/webconsole/$"
        % (PVAR_REGION, PVAR_NAME, PVAR_PROCESS_TYPE, PVAR_PROCESS_INSTANCE_NAME),
        views.ProcessInstanceViewSet.as_view({'post': 'create_webconsole'}),
    ),
    # App BuildProcesses
    re_path(
        r"^regions/%s/apps/%s/build_processes/$" % (PVAR_REGION, PVAR_NAME),
        views.BuildProcessViewSet.as_view({'post': 'create_build_process'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/build_processes/%s/result" % (PVAR_REGION, PVAR_NAME, PVAR_UUID),
        views.BuildProcessResultViewSet.as_view({'get': 'retrieve'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/build_processes/%s/interruptions/" % (PVAR_REGION, PVAR_NAME, PVAR_UUID),
        views.BuildProcessViewSet.as_view({'post': 'user_interrupt'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/builds/$" % (PVAR_REGION, PVAR_NAME),
        views.BuildViewSet.as_view({'get': 'list'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/builds/placeholder/$" % (PVAR_REGION, PVAR_NAME),
        views.BuildViewSet.as_view({'post': 'create_placeholder'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/builds/%s$" % (PVAR_REGION, PVAR_NAME, PVAR_UUID),
        views.BuildViewSet.as_view({'get': 'retrieve'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/releases/$" % (PVAR_REGION, PVAR_NAME),
        views.ReleaseViewSet.as_view({'post': 'create_release', 'get': 'retrieve'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/archive/$" % (PVAR_REGION, PVAR_NAME),
        views.ArchiveViewSet.as_view({'post': 'archive'}),
    ),
    # App Config
    re_path(
        r"^regions/%s/apps/%s/config/$" % (PVAR_REGION, PVAR_NAME),
        views.ConfigViewSet.as_view({'get': 'retrieve', 'post': 'update_config'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/config/metadata$" % (PVAR_REGION, PVAR_NAME),
        views.ConfigViewSet.as_view({'post': 'update_metadata'}),
    ),
    ####################
    # Resource Metrics #
    ####################
    re_path(
        r"^regions/%s/apps/%s/processes/%s/instances/%s/metrics/$"
        % (PVAR_REGION, PVAR_NAME, PVAR_PROCESS_TYPE, PVAR_PROCESS_INSTANCE_NAME),
        views.ResourceMetricsViewSet.as_view({'get': 'query'}),
    ),
    re_path(
        r"^regions/%s/apps/%s/processes/%s/metrics/$" % (PVAR_REGION, PVAR_NAME, PVAR_PROCESS_TYPE),
        views.ResourceMetricsViewSet.as_view({'get': 'multi_query'}),
    ),
]

urlpatterns += [
    re_path(
        make_app_path(r'/addresses/$', include_envs=False),
        views.EnvDeployedStatusViewSet.as_view({'get': 'list_addrs'}),
    ),
]
