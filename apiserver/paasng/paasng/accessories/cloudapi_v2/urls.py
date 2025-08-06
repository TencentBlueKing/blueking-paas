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

from .mcp_servers import views

urlpatterns = [
    # 获取 mcp-server 列表
    path(
        "api/cloudapi-v2/apps/<slug:app_code>/inner/mcp-servers/",
        views.MCPServerAPIViewSet.as_view({"get": "list_mcp_servers"}),
        name="api.cloudapi.v2.mcp_servers",
    ),
    # 获取 app mcp-server 权限列表
    path(
        "api/cloudapi-v2/apps/<slug:app_code>/inner/mcp-servers/permissions/",
        views.MCPServerAPIViewSet.as_view({"get": "list_app_mcp_server_permissions"}),
        name="api.cloudapi.v2.app_mcp_server_permissions",
    ),
    # 批量申请权限
    path(
        "api/cloudapi-v2/apps/<slug:app_code>/inner/mcp-servers/permissions/apply/",
        views.MCPServerAPIViewSet.as_view({"post": "apply_mcp_server_permissions"}),
        name="api.cloudapi.v2.mcp_server_permissions_apply",
    ),
    # 权限申请记录
    path(
        "api/cloudapi-v2/apps/<slug:app_code>/inner/mcp-servers/permissions/apply-records/",
        views.MCPServerAPIViewSet.as_view({"get": "list_mcp_server_permissions_apply_records"}),
        name="api.cloudapi.v2.mcp_server_permissions_apply_records",
    ),
]
