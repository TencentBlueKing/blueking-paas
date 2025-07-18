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

from django.urls import path

from paas_wl.apis.admin.views import certs, domain, logs, processes

urlpatterns = [
    # 应用资源方案-API
    path(
        "wl_api/platform/process_spec_plan/manage/",
        processes.ProcessSpecPlanManageViewSet.as_view({"get": "get_context_data"}),
    ),
    path(
        "wl_api/platform/process_spec_plan/",
        processes.ProcessSpecPlanManageViewSet.as_view(dict(post="create", get="list")),
        name="wl_api.process_spec_plan",
    ),
    path(
        "wl_api/platform/process_spec_plan/id/<int:id>/",
        processes.ProcessSpecPlanManageViewSet.as_view(dict(put="edit", get="list_binding_app")),
        name="wl_api.process_spec_plan_by_id",
    ),
    path(
        "wl_api/apps/<str:name>/processes/<str:process_type>/plan",
        processes.ProcessSpecManageViewSet.as_view({"put": "switch_process_plan"}),
        name="wl_api.application.process_plan",
    ),
    path(
        "wl_api/apps/<str:name>/processes/<str:process_type>/scale",
        processes.ProcessSpecManageViewSet.as_view({"put": "scale"}),
        name="wl_api.application.process_scale",
    ),
    path(
        "wl_api/apps/<str:name>/processes/<str:process_type>/instances/<str:instance_name>/",
        processes.ProcessInstanceViewSet.as_view({"get": "retrieve"}),
        name="wl_api.application.process_instance",
    ),
    # 独立域名相关 API
    path(
        "wl_api/applications/<str:code>/domains/",
        domain.AppDomainsViewSet.as_view({"get": "list", "post": "create"}),
        name="wl_api.application.domains",
    ),
    path(
        "wl_api/applications/<str:code>/domains/<int:id>/",
        domain.AppDomainsViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="wl_api.application.domain_by_id",
    ),
    # Shared certificates
    path(
        "wl_api/platform/app_certs/shared/",
        certs.AppDomainSharedCertsViewSet.as_view({"post": "create", "get": "list"}),
        name="wl_api.shared_app_certs",
    ),
    path(
        "wl_api/platform/app_certs/shared/<str:name>",
        certs.AppDomainSharedCertsViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="wl_api.shared_app_cert_by_name",
    ),
    # 日志采集管理
    path(
        "wl_api/applications/<str:code>/log_config/",
        logs.AppLogConfigViewSet.as_view({"get": "list", "post": "toggle"}),
        name="wl_api.application.log_config",
    ),
]
