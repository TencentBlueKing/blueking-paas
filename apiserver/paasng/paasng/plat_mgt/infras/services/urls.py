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

from paasng.plat_mgt.infras.services import views

urlpatterns = [
    path(
        "api/plat_mgt/infras/plans/",
        views.PlanViewSet.as_view({"get": "list_all"}),
        name="plat_mgt.infras.services.plans.list_all",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/plans/",
        views.PlanViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.services.plans.bulk",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/plans/<str:plan_id>/",
        views.PlanViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="plat_mgt.infras.services.plans.detail",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/binding-policies/",
        views.BindingPolicyViewSet.as_view(
            {"get": "retrieve", "post": "upsert", "put": "upsert", "delete": "destroy"}
        ),
        name="plat_mgt.infras.services.binding-policies.detail",
    ),
]
