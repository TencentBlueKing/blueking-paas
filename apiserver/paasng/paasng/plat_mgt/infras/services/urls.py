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
    # 平台管理-增强服务-服务管理 API
    path(
        "api/plat_mgt/infras/services/",
        views.ServiceViewSet.as_view({"get": "list", "post": "create"}),
        name="plat_mgt.infras.services",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/",
        views.ServiceViewSet.as_view({"put": "update", "delete": "destroy"}),
        name="plat_mgt.infras.services.detail",
    ),
    # 平台管理-增强服务-服务方案 API
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
    # 平台管理-增强服务管理-资源池
    path(
        "api/plat_mgt/infras/pre_created_instances/",
        views.PreCreatedInstanceViewSet.as_view({"get": "list_all_pre_created_instances"}),
        name="plat_mgt.infras.pre_created_instances.list_all",
    ),
    path(
        "api/plat_mgt/infras/plans/<str:plan_id>/pre_created_instances/",
        views.PreCreatedInstanceViewSet.as_view({"post": "create", "get": "list"}),
        name="plat_mgt.infras.pre_created_instances",
    ),
    path(
        "api/plat_mgt/infras/plans/<str:plan_id>/pre_created_instances/<str:instance_id>/",
        views.PreCreatedInstanceViewSet.as_view({"delete": "destroy", "put": "update"}),
        name="plat_mgt.infras.pre_created_instances.detail",
    ),
    # 分配策略相关 API
    path(
        "api/plat_mgt/infras/service_binding_policy_condition_types/",
        views.BindingPolicyViewSet.as_view({"get": "list_condition_types"}),
        name="plat_mgt.infras.binding-policiey.list_condition_types",
    ),
    path(
        "api/plat_mgt/infras/services/<str:service_id>/binding_policies/",
        views.BindingPolicyViewSet.as_view({"get": "list", "post": "upsert", "put": "upsert", "delete": "destroy"}),
        name="plat_mgt.infras.services.binding-policies.detail",
    ),
    path(
        "api/plat_mgt/infras/service_category/",
        views.CategoryViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.services.category.list",
    ),
    path(
        "api/plat_mgt/infras/service_provider_choices/",
        views.ProviderViewSet.as_view({"get": "list"}),
        name="plat_mgt.infras.services.provider_choices.list",
    ),
]
