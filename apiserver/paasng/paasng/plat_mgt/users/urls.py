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

from paasng.plat_mgt.users import views

urlpatterns = [
    # 平台管理员
    path(
        "api/plat_mgt/users/admin_user/",
        views.PlatformManagerViewSet.as_view({"get": "list", "post": "bulk_create"}),
        name="plat_mgt.users.admin_user.bulk",
    ),
    path(
        "api/plat_mgt/users/admin_user/<str:user>/",
        views.PlatformManagerViewSet.as_view({"delete": "destroy"}),
        name="plat_mgt.users.admin_user.delete",
    ),
    # 用户特性
    path(
        "api/plat_mgt/users/account_feature_flags/",
        views.AccountFeatureFlagViewSet.as_view({"get": "list", "post": "upsert"}),
        name="plat_mgt.users.account_feature_flags.bulk",
    ),
    path(
        "api/plat_mgt/users/account_feature_flags/<str:id>/",
        views.AccountFeatureFlagViewSet.as_view({"delete": "destroy"}),
        name="plat_mgt.users.account_feature_flags.delete",
    ),
    # 用户特性种类列表
    path(
        "api/plat_mgt/users/account_features/",
        views.AccountFeatureFlagViewSet.as_view({"get": "feature_list"}),
        name="plat_mgt.users.account_features.feature_list",
    ),
    # 系统 API 用户
    path(
        "api/plat_mgt/users/system_api_user/",
        views.SystemApiUserViewSet.as_view({"get": "list", "post": "create", "put": "update"}),
        name="plat_mgt.users.system_api_user.bulk",
    ),
    path(
        "api/plat_mgt/users/system_api_user/<str:name>/",
        views.SystemApiUserViewSet.as_view({"delete": "destroy"}),
        name="plat_mgt.users.system_api_user.delete",
    ),
    path(
        "api/plat_mgt/users/system_api_roles/",
        views.SystemApiUserViewSet.as_view({"get": "role_list"}),
        name="plat_mgt.users.system_api_roles.role_list",
    ),
]
