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
        make_app_pattern(r"/processes/$"),
        views.ProcessesViewSet.as_view({"post": "update"}),
        name="api.processes.update",
    ),
    # Cloud-native type application, list and watch processes of an environment, the result
    # include multiple modules.
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/envs/(?P<environment>stag|prod)/processes/list/$",
        views.CNativeListAndWatchProcsViewSet.as_view({"get": "list"}),
        name="api.list_processes.namespace_scoped",
    ),
    re_path(
        r"api/bkapps/applications/(?P<code>[^/]+)/envs/(?P<environment>stag|prod)/processes/watch/$",
        views.CNativeListAndWatchProcsViewSet.as_view({"get": "watch"}),
        name="api.watch_processes.namespace_scoped",
    ),
    # Below paths using legacy prefix.
    #
    # Default type application, list and watch processes of an environment, the result
    # only include one module.
    re_path(
        make_app_pattern(r"/processes/list/$"),
        views.ListAndWatchProcsViewSet.as_view({"get": "list"}),
        name="api.list_processes",
    ),
    re_path(
        make_app_pattern(r"/processes/watch/$"),
        views.ListAndWatchProcsViewSet.as_view({"get": "watch"}),
        name="api.watch_processes",
    ),
    re_path(
        make_app_pattern(r"/instance_events/(?P<instance_name>.+)/$"),
        views.InstanceEventsViewSet.as_view({"get": "list"}),
        name="api.list_instance_events",
    ),
    re_path(
        make_app_pattern(r"/processes/(?P<process_type>[\w-]+)/instances/(?P<process_instance_name>[.\w-]+)/logs/$"),
        views.InstanceManageViewSet.as_view({"get": "retrieve_logs"}),
        name="api.instances.logs",
    ),
    re_path(
        make_app_pattern(
            r"/processes/(?P<process_type>[\w-]+)/instances/(?P<process_instance_name>[.\w-]+)/logs/download/$"
        ),
        views.InstanceManageViewSet.as_view({"get": "download_logs"}),
        name="api.instances.logs_download",
    ),
    re_path(
        make_app_pattern(
            r"/processes/(?P<process_type>[\w-]+)/instances/(?P<process_instance_name>[.\w-]+)/logs/stream/$"
        ),
        views.InstanceManageViewSet.as_view({"get": "logs_stream"}),
        name="api.instances.logs_stream",
    ),
    re_path(
        make_app_pattern(r"/instances/(?P<process_instance_name>[.\w-]+)/restart/$"),
        views.InstanceManageViewSet.as_view({"put": "restart"}),
        name="api.instances.restart",
    ),
    re_path(
        make_app_pattern(r"/processes/(?P<process_name>[\w-]+)/restart/$"),
        views.ProcessesViewSet.as_view({"put": "restart"}),
        name="api.process.restart",
    ),
]
