# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from .sandbox_views import E2BSandboxViewSet
from .views import E2BApiKeyViewSet

# e2b 协议端点的挂载前缀。用户侧要设 E2B_API_URL=https://<domain>/api/agent_sandbox/e2b，
# SDK 拿它当 httpx 的 base_url，再接协议规定的相对路径（/sandboxes、/v2/sandboxes 等）。
E2B_PROTOCOL_PREFIX = "api/agent_sandbox/e2b/"

urlpatterns = [
    path(
        "api/agent_sandbox/applications/<slug:code>/e2b/api_keys/",
        E2BApiKeyViewSet.as_view({"post": "create", "get": "list"}),
        name="agent_sandbox.e2b.api_key",
    ),
    path(
        "api/agent_sandbox/applications/<slug:code>/e2b/api_keys/<uuid:key_id>",
        E2BApiKeyViewSet.as_view({"delete": "destroy"}),
        name="agent_sandbox.e2b.api_key.destroy",
    ),
    path(
        E2B_PROTOCOL_PREFIX + "sandboxes",
        E2BSandboxViewSet.as_view({"post": "create"}),
        name="agent_sandbox.e2b.sandboxes.create",
    ),
    path(
        E2B_PROTOCOL_PREFIX + "v2/sandboxes",
        E2BSandboxViewSet.as_view({"get": "list"}),
        name="agent_sandbox.e2b.sandboxes.list",
    ),
    path(
        E2B_PROTOCOL_PREFIX + "sandboxes/<str:sandbox_id>",
        E2BSandboxViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="agent_sandbox.e2b.sandboxes.detail",
    ),
    path(
        E2B_PROTOCOL_PREFIX + "sandboxes/<str:sandbox_id>/timeout",
        E2BSandboxViewSet.as_view({"post": "set_timeout"}),
        name="agent_sandbox.e2b.sandboxes.timeout",
    ),
]
