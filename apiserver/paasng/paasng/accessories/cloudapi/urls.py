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

urlpatterns = [
    # 网关API相关接口
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/",
        views.CloudAPIViewSet.as_view({"get": "list_apis"}),
        name="api.cloudapi.v1.apis",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/<int:api_id>/permissions/resources/",
        views.CloudAPIViewSet.as_view({"get": "list_resource_permissions"}),
        name="api.cloudapi.v1.resource_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/<int:api_id>/permissions/apply/",
        views.CloudAPIViewSet.as_view({"post": "apply"}),
        name="api.cloudapi.v1.apply_resource_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/permissions/renew/",
        views.CloudAPIViewSet.as_view({"post": "renew"}),
        name="api.cloudapi.v1.renew_resource_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/<int:api_id>/permissions/allow-apply-by-api/",
        views.CloudAPIViewSet.as_view({"get": "allow_apply_by_api"}),
        name="api.cloudapi.v1.allow_apply_by_api",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/permissions/app-permissions/",
        views.CloudAPIViewSet.as_view({"get": "list_app_resource_permissions"}),
        name="api.cloudapi.v1.list_app_resource_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/permissions/apply-records/",
        views.CloudAPIViewSet.as_view({"get": "list_resource_permission_apply_records"}),
        name="api.cloudapi.v1.list_resource_permission_apply_records",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/apis/permissions/apply-records/<int:record_id>/",
        views.CloudAPIViewSet.as_view({"get": "retrieve_resource_permission_apply_record"}),
        name="api.cloudapi.v1.retrieve_resource_permission_apply_record",
    ),
    # 组件API相关接口
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/",
        views.CloudAPIViewSet.as_view({"get": "list_esb_systems"}),
        name="api.cloudapi.v1.systems",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/<int:system_id>/permissions/components/",
        views.CloudAPIViewSet.as_view({"get": "list_component_permissions"}),
        name="api.cloudapi.v1.component_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/<int:system_id>/permissions/apply/",
        views.CloudAPIViewSet.as_view({"post": "apply_component_permissions"}),
        name="api.cloudapi.v1.apply_component_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/permissions/renew/",
        views.CloudAPIViewSet.as_view({"post": "renew_component_permissions"}),
        name="api.cloudapi.v1.renew_component_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/permissions/app-permissions/",
        views.CloudAPIViewSet.as_view({"get": "list_app_component_permissions"}),
        name="api.cloudapi.v1.list_app_component_permissions",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/permissions/apply-records/",
        views.CloudAPIViewSet.as_view({"get": "list_component_permission_apply_records"}),
        name="api.cloudapi.v1.list_component_permission_apply_records",
    ),
    path(
        "api/cloudapi/apps/<slug:app_code>/esb/systems/permissions/apply-records/<int:record_id>/",
        views.CloudAPIViewSet.as_view({"get": "retrieve_component_permission_apply_record"}),
        name="api.cloudapi.v1.retrieve_component_permission_apply_record",
    ),
]
