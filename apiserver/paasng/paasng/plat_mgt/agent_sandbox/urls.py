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

from django.urls import re_path

from .views import E2BBuiltinTemplateViewSet, E2BTemplateSyncViewSet

urlpatterns = [
    re_path(
        r"^api/plat_mgt/agent_sandbox/e2b/templates/$",
        E2BBuiltinTemplateViewSet.as_view({"get": "list", "post": "create"}),
        name="plat_mgt.agent_sandbox.e2b.templates.list_create",
    ),
    re_path(
        r"^api/plat_mgt/agent_sandbox/e2b/templates/(?P<template_id>[^/]+)/$",
        E2BBuiltinTemplateViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="plat_mgt.agent_sandbox.e2b.templates.retrieve_update_destroy",
    ),
    # 不挂在 templates/ 下，避免与模板标识冲突
    re_path(
        r"^api/plat_mgt/agent_sandbox/e2b/template_sync/$",
        E2BTemplateSyncViewSet.as_view({"post": "sync"}),
        name="plat_mgt.agent_sandbox.e2b.template_sync",
    ),
    re_path(
        r"^api/plat_mgt/agent_sandbox/e2b/template_sync/templates/$",
        E2BTemplateSyncViewSet.as_view({"get": "list_templates"}),
        name="plat_mgt.agent_sandbox.e2b.template_sync.templates",
    ),
    re_path(
        r"^api/plat_mgt/agent_sandbox/e2b/template_sync/clusters/$",
        E2BTemplateSyncViewSet.as_view({"get": "list_clusters"}),
        name="plat_mgt.agent_sandbox.e2b.template_sync.clusters",
    ),
]
