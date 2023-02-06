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

from paas_wl.admin.views import certs, clusters, domain, processes

urlpatterns = [
    # 平台管理-应用资源方案-API
    path(
        'admin42/platform/process_spec_plan/manage/',
        processes.ProcessSpecPlanManageViewSet.as_view({"get": "get_context_data"}),
        name="admin.process_spec_plan.manage",
    ),
    path(
        'admin42/platform/process_spec_plan/',
        processes.ProcessSpecPlanManageViewSet.as_view(dict(post="create", get="list")),
        name="admin.process_spec_plan",
    ),
    path(
        'admin42/platform/process_spec_plan/id/<int:id>/',
        processes.ProcessSpecPlanManageViewSet.as_view(dict(put="edit", get="list_binding_app")),
        name="admin.process_spec_plan.detail",
    ),
    path(
        "admin42/regions/<str:region>/apps/<str:name>/processes/<str:process_type>/plan",
        processes.ProcessSpecManageViewSet.as_view({'put': 'switch_process_plan'}),
    ),
    path(
        "admin42/regions/<str:region>/apps/<str:name>/processes/<str:process_type>/scale",
        processes.ProcessSpecManageViewSet.as_view({'put': 'scale'}),
    ),
    path(
        "admin42/regions/<str:region>/apps/<str:name>/processes/<str:process_type>/instances/<str:instance_name>/",
        processes.ProcessInstanceViewSet.as_view({'get': 'retrieve'}),
    ),
    # 独立域名相关 API
    path(
        'admin42/applications/<str:code>/domains/',
        domain.AppDomainsViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='admin.app_domains',
    ),
    path(
        'admin42/applications/<str:code>/domains/<int:id>/',
        domain.AppDomainsViewSet.as_view({'put': 'update', 'delete': 'destroy'}),
        name='admin.app_domains.singular',
    ),
    # Shared certificates
    path(
        'admin42/platform/app_certs/shared/',
        certs.AppDomainSharedCertsViewSet.as_view({'post': 'create', 'get': 'list'}),
    ),
    path(
        'admin42/platform/app_certs/shared/<str:name>',
        certs.AppDomainSharedCertsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
    ),
    # 平台管理-集群管理API
    path(
        'admin42/platform/clusters/',
        clusters.ClusterViewSet.as_view({'post': 'update_or_create', 'get': 'list'}),
    ),
    path(
        'admin42/platform/clusters/gen_state/',
        clusters.ClusterViewSet.as_view({'post': 'gen_state'}),
    ),
    path(
        'admin42/platform/clusters/operator/',
        clusters.ClusterViewSet.as_view({'get': 'list_operator_infos'}),
    ),
    path(
        'admin42/platform/clusters/<str:pk>/',
        clusters.ClusterViewSet.as_view({'get': 'retrieve', 'put': 'update_or_create', 'delete': 'destroy'}),
    ),
    path(
        'admin42/platform/clusters/<str:pk>/api_servers',
        clusters.ClusterViewSet.as_view({'post': 'bind_api_server'}),
    ),
    path(
        'admin42/platform/clusters/<str:pk>/api_servers/<str:api_server_id>',
        clusters.ClusterViewSet.as_view({'delete': 'unbind_api_server'}),
    ),
]
