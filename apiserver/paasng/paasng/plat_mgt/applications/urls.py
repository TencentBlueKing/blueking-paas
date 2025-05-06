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

from paasng.plat_mgt.applications.views import application

urlpatterns = [
    # 平台管理 - 应用列表
    path(
        "api/plat_mgt/applications/",
        application.ApplicationView.as_view({"get": "list"}),
        name="plat_mgt.applications.list_applications",
    ),
    path(
        "api/plat_mgt/applications/tenant_id_list/",
        application.ApplicationView.as_view({"get": "list_tenant_id"}),
        name="plat_mgt.applications.list_tenant_id",
    ),
    path(
        "api/plat_mgt/applications/tenant_mode_list/",
        application.ApplicationView.as_view({"get": "list_tenant_mode"}),
        name="plat_mgt.applications.list_tenant_mode",
    ),
    path(
        "api/plat_mgt/applications/types/",
        application.ApplicationView.as_view({"get": "list_app_types"}),
        name="plat_mgt.applications.types",
    ),
]
