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

from . import views

urlpatterns = [
    # ============ 网关 API 相关 ============
    # 获取网关列表
    path(
        "apps/<slug:app_code>/inner/gateways/",
        views.GatewayAPIViewSet.as_view({"get": "list_gateways"}),
        name="api.cloudapi.v2.gateways",
    ),
    # 获取单个网关详情
    path(
        "apps/<slug:app_code>/inner/gateways/<slug:gateway_name>/",
        views.GatewayAPIViewSet.as_view({"get": "get_gateway"}),
        name="api.cloudapi.v2.gateway_detail",
    ),
    # 获取网关资源列表（权限申请用）
    path(
        "apps/<slug:app_code>/inner/gateways/<slug:gateway_name>/permissions/resources/",
        views.GatewayAPIViewSet.as_view({"get": "list_gateway_permission_resources"}),
        name="api.cloudapi.v2.gateway_permission_resources",
    ),
    # 是否允许按网关申请资源权限
    path(
        "apps/<slug:app_code>/inner/gateways/<slug:gateway_name>/permissions/allow-apply-by-gateway/",
        views.GatewayAPIViewSet.as_view({"get": "check_is_allowed_apply_by_gateway"}),
        name="api.cloudapi.v2.gateway_allow_apply_by_gateway",
    ),
    # 网关资源权限申请
    path(
        "apps/<slug:app_code>/inner/gateways/<slug:gateway_name>/permissions/apply/",
        views.GatewayAPIViewSet.as_view({"post": "apply_gateway_resource_permission"}),
        name="api.cloudapi.v2.gateway_permission_apply",
    ),
    # 已申请的资源权限列表
    path(
        "apps/<slug:app_code>/inner/gateways/permissions/app-permissions/",
        views.GatewayAPIViewSet.as_view({"get": "list_app_resource_permissions"}),
        name="api.cloudapi.v2.app_resource_permissions",
    ),
    # 权限续期
    path(
        "apps/<slug:app_code>/inner/gateways/permissions/renew/",
        views.GatewayAPIViewSet.as_view({"post": "renew_resource_permission"}),
        name="api.cloudapi.v2.resource_permission_renew",
    ),
    # 资源权限申请记录列表
    path(
        "apps/<slug:app_code>/inner/gateways/permissions/apply-records/",
        views.GatewayAPIViewSet.as_view({"get": "list_resource_permission_apply_records"}),
        name="api.cloudapi.v2.resource_permission_apply_records",
    ),
    # 资源权限申请记录详情
    path(
        "apps/<slug:app_code>/inner/gateways/permissions/apply-records/<int:record_id>/",
        views.GatewayAPIViewSet.as_view({"get": "retrieve_resource_permission_apply_record"}),
        name="api.cloudapi.v2.resource_permission_apply_record_detail",
    ),
    # ============ ESB 组件 API 相关 ============
    # 查询组件系统列表
    path(
        "apps/<slug:app_code>/inner/esb/systems/",
        views.GatewayAPIViewSet.as_view({"get": "list_esb_systems"}),
        name="api.cloudapi.v2.esb_systems",
    ),
    # 查询系统权限组件
    path(
        "apps/<slug:app_code>/inner/esb/systems/<int:system_id>/permissions/components/",
        views.GatewayAPIViewSet.as_view({"get": "list_esb_system_permission_components"}),
        name="api.cloudapi.v2.esb_system_permission_components",
    ),
    # 创建申请 ESB 组件权限的申请单据
    path(
        "apps/<slug:app_code>/inner/esb/systems/<int:system_id>/permissions/apply/",
        views.GatewayAPIViewSet.as_view({"post": "apply_esb_system_component_permissions"}),
        name="api.cloudapi.v2.esb_system_component_permission_apply",
    ),
    # ESB 组件权限续期
    path(
        "apps/<slug:app_code>/inner/esb/systems/permissions/renew/",
        views.GatewayAPIViewSet.as_view({"post": "renew_esb_component_permissions"}),
        name="api.cloudapi.v2.esb_component_permission_renew",
    ),
    # 已申请的 ESB 组件权限列表
    path(
        "apps/<slug:app_code>/inner/esb/systems/permissions/app-permissions/",
        views.GatewayAPIViewSet.as_view({"get": "list_app_esb_component_permissions"}),
        name="api.cloudapi.v2.app_esb_component_permissions",
    ),
    # 查询应用权限申请记录列表
    path(
        "apps/<slug:app_code>/inner/esb/systems/permissions/apply-records/",
        views.GatewayAPIViewSet.as_view({"get": "list_app_esb_component_permission_apply_records"}),
        name="api.cloudapi.v2.esb_component_permission_apply_records",
    ),
    # 查询应用权限申请记录详情
    path(
        "apps/<slug:app_code>/inner/esb/systems/permissions/apply-records/<int:record_id>/",
        views.GatewayAPIViewSet.as_view({"get": "get_app_esb_component_permission_apply_record"}),
        name="api.cloudapi.v2.esb_component_permission_apply_record_detail",
    ),
]
