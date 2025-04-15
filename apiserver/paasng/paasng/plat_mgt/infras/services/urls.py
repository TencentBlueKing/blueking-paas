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
        "api/plat_mgt/infras/services/",
        views.AddonsServiceViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.services.list",
    ),
    path(
        "api/plat_mgt/infras/plans/",
        views.PlanViewSet.as_view({"get": "list_all"}),
        name="plat_mgt.infras.services.plans.list_all",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/tenants/<str:tenant_id>/plans/",
        views.PlanViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.services.tenants.plans.bulk",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/tenants/<str:tenant_id>/plans/<str:plan_id>/",
        views.PlanViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="plat_mgt.infras.services.plans.detail",
    ),
    # 集群分配策略相关
    path(
        "api/plat_mgt/infras/service_binding_policy_condition_types/",
        views.BindingPolicyViewSet.as_view({"get": "list_condition_types"}),
        name="plat_mgt.infras.binding-policiey.list_condition_types",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/binding-policies/",
        views.BindingPolicyViewSet.as_view({"get": "list", "post": "upsert", "put": "upsert", "delete": "destroy"}),
        name="plat_mgt.infras.services.binding-policies.detail",
    ),
    path(
        "api/plat_mgt/infras/services/category/",
        views.CategoryViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.services.category.list",
    ),
    path(
        "api/plat_mgt/infras/services/provider_choices/",
        views.ProviderViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.services.provider_choices.list",
    ),
]
