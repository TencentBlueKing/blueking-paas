# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property


class Group(OperationGroup):
    # 查询分级管理员列表
    management_grade_managers_list = bind_property(
        Operation, name="management_grade_managers_list", method="GET", path="/api/v1/open/management/grade_managers/"
    )

    # 创建分级管理员
    management_grade_managers = bind_property(
        Operation, name="management_grade_managers", method="POST", path="/api/v1/open/management/grade_managers/"
    )

    # 分级管理员成员列表
    management_grade_manager_members = bind_property(
        Operation,
        name="management_grade_manager_members",
        method="GET",
        path="/api/v1/open/management/grade_managers/{id}/members/",
    )

    # 批量添加分级管理员成员
    management_add_grade_manager_members = bind_property(
        Operation,
        name="management_add_grade_manager_members",
        method="POST",
        path="/api/v1/open/management/grade_managers/{id}/members/",
    )

    # 批量删除分级管理员成员
    management_delete_grade_manager_members = bind_property(
        Operation,
        name="management_delete_grade_manager_members",
        method="DELETE",
        path="/api/v1/open/management/grade_managers/{id}/members/",
    )

    # 分级管理员批量创建用户组
    v2_management_grade_manager_create_groups = bind_property(
        Operation,
        name="v2_management_grade_manager_create_groups",
        method="POST",
        path="/api/v2/open/management/systems/{system_id}/grade_managers/{id}/groups/",
    )

    # 删除用户组
    v2_management_grade_manager_delete_group = bind_property(
        Operation,
        name="v2_management_grade_manager_delete_group",
        method="DELETE",
        path="/api/v2/open/management/systems/{system_id}/groups/{group_id}/",
    )

    # 用户组成员列表
    v2_management_group_members = bind_property(
        Operation,
        name="v2_management_group_members",
        method="GET",
        path="/api/v2/open/management/systems/{system_id}/groups/{group_id}/members/",
    )

    # 用户组添加成员
    v2_management_add_group_members = bind_property(
        Operation,
        name="v2_management_add_group_members",
        method="POST",
        path="/api/v2/open/management/systems/{system_id}/groups/{group_id}/members/",
    )

    # 用户组删除成员
    v2_management_delete_group_members = bind_property(
        Operation,
        name="v2_management_delete_group_members",
        method="DELETE",
        path="/api/v2/open/management/systems/{system_id}/groups/{group_id}/members/",
    )

    # 用户组授权
    v2_management_groups_policies_grant = bind_property(
        Operation,
        name="v2_management_groups_policies_grant",
        method="POST",
        path="/api/v2/open/management/systems/{system_id}/groups/{group_id}/policies/",
    )


class Client(APIGatewayClient):
    """蓝鲸权限中心提供的 OpenAPI"""

    _api_name = "bk-iam"

    api = bind_property(Group, name="api")
