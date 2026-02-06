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

from .views import AgentSandboxFSViewSet, AgentSandboxViewSet

PVAR_UUID = r"(?P<sandbox_id>[0-9a-f-]{32,36})"

urlpatterns = [
    path(
        "api/agent_sandbox/applications/<slug:code>/sandboxes/",
        AgentSandboxViewSet.as_view({"post": "create"}),
        name="agent_sandbox.create",
    ),
    # Sandbox URLs by UUID
    path(
        "api/agent_sandbox/sandboxes/<str:sandbox_id>",
        AgentSandboxViewSet.as_view({"delete": "destroy"}),
        name="agent_sandbox.destroy",
    ),
    # Filesystem related URLs
    path(
        "api/agent_sandbox/sandboxes/<str:sandbox_id>/folders/create",
        AgentSandboxFSViewSet.as_view({"post": "create_folder"}),
        name="agent_sandbox.fs.create_folder",
    ),
    path(
        "api/agent_sandbox/sandboxes/<str:sandbox_id>/files/upload",
        AgentSandboxFSViewSet.as_view({"post": "upload_file"}),
        name="agent_sandbox.fs.upload_file",
    ),
    path(
        "api/agent_sandbox/sandboxes/<str:sandbox_id>/files/delete",
        AgentSandboxFSViewSet.as_view({"post": "delete_file"}),
        name="agent_sandbox.fs.delete_file",
    ),
    path(
        "api/agent_sandbox/sandboxes/<str:sandbox_id>/files/download",
        AgentSandboxFSViewSet.as_view({"get": "download_file"}),
        name="agent_sandbox.fs.download_file",
    ),
]
