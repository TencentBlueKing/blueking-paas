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

from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property


class Group(OperationGroup):
    """网关 bkiam 的 Operation 定义

    V4 的接口按用途分为鉴权、模型注册、管理空间与用户组、授权、跨系统共享、申请链接六类。
    各类接口由对应的子需求在此按类追加 `bind_property(Operation, ...)` 定义，
    调用时统一经 `paasng.infras.iam.v4.http.BKIAMV4BaseClient` 发起，
    以复用其 header 注入、翻页、分批与错误处理逻辑。
    """

    # ---------------- 鉴权 ----------------
    # 三个鉴权接口均为读操作，调用时不注入操作人 header。
    # 系统标识由 path 参数 system_id 承载，资源类型由 action 隐含，故请求体中的资源实例只有 id。

    # 直接鉴权：单个用户对单个资源实例的单个操作
    direct_auth = bind_property(
        Operation,
        name="direct_auth",
        method="POST",
        path="/api/v1/open/rbac/authorization/systems/{system_id}/auth/",
    )

    # 批量操作鉴权：单个资源实例上一次判定多个操作，单次上限 20 个操作，
    # 且这些操作须关联相同的资源类型或均为资源无关的操作
    direct_auth_by_actions = bind_property(
        Operation,
        name="direct_auth_by_actions",
        method="POST",
        path="/api/v1/open/rbac/authorization/systems/{system_id}/auth-by-actions/",
    )

    # 批量资源鉴权：单个操作上一次判定多个资源实例，单次上限 20 个资源
    direct_auth_by_resources = bind_property(
        Operation,
        name="direct_auth_by_resources",
        method="POST",
        path="/api/v1/open/rbac/authorization/systems/{system_id}/auth-by-resources/",
    )

    # ---------------- 模型注册：系统 ----------------
    create_system = bind_property(
        Operation, name="create_system", method="POST", path="/api/v1/open/rbac/model/systems/"
    )
    retrieve_system = bind_property(
        Operation, name="retrieve_system", method="GET", path="/api/v1/open/rbac/model/systems/{system_id}/"
    )
    update_system = bind_property(
        Operation, name="update_system", method="PUT", path="/api/v1/open/rbac/model/systems/{system_id}/"
    )

    # ---------------- 模型注册：资源类型 ----------------
    list_resource_type = bind_property(
        Operation,
        name="list_resource_type",
        method="GET",
        path="/api/v1/open/rbac/model/systems/{system_id}/resource-types/",
    )
    batch_create_resource_type = bind_property(
        Operation,
        name="batch_create_resource_type",
        method="POST",
        path="/api/v1/open/rbac/model/systems/{system_id}/resource-types/",
    )
    update_resource_type = bind_property(
        Operation,
        name="update_resource_type",
        method="PUT",
        path="/api/v1/open/rbac/model/systems/{system_id}/resource-types/{resource_type_id}/",
    )
    delete_resource_type = bind_property(
        Operation,
        name="delete_resource_type",
        method="DELETE",
        path="/api/v1/open/rbac/model/systems/{system_id}/resource-types/{resource_type_id}/",
    )

    # ---------------- 模型注册：操作 ----------------
    list_action = bind_property(
        Operation, name="list_action", method="GET", path="/api/v1/open/rbac/model/systems/{system_id}/actions/"
    )
    batch_create_action = bind_property(
        Operation,
        name="batch_create_action",
        method="POST",
        path="/api/v1/open/rbac/model/systems/{system_id}/actions/",
    )
    update_action = bind_property(
        Operation,
        name="update_action",
        method="PUT",
        path="/api/v1/open/rbac/model/systems/{system_id}/actions/{action_id}/",
    )
    delete_action = bind_property(
        Operation,
        name="delete_action",
        method="DELETE",
        path="/api/v1/open/rbac/model/systems/{system_id}/actions/{action_id}/",
    )

    # ---------------- 模型注册：角色 ----------------
    list_role = bind_property(
        Operation, name="list_role", method="GET", path="/api/v1/open/rbac/model/systems/{system_id}/roles/"
    )
    batch_create_role = bind_property(
        Operation, name="batch_create_role", method="POST", path="/api/v1/open/rbac/model/systems/{system_id}/roles/"
    )
    update_role = bind_property(
        Operation,
        name="update_role",
        method="PUT",
        path="/api/v1/open/rbac/model/systems/{system_id}/roles/{role_id}/",
    )
    delete_role = bind_property(
        Operation,
        name="delete_role",
        method="DELETE",
        path="/api/v1/open/rbac/model/systems/{system_id}/roles/{role_id}/",
    )
    batch_create_role_action = bind_property(
        Operation,
        name="batch_create_role_action",
        method="POST",
        path="/api/v1/open/rbac/model/systems/{system_id}/roles/{role_id}/actions/",
    )
    batch_delete_role_action = bind_property(
        Operation,
        name="batch_delete_role_action",
        method="DELETE",
        path="/api/v1/open/rbac/model/systems/{system_id}/roles/{role_id}/actions/",
    )


class Client(APIGatewayClient):
    """蓝鲸权限中心 V4 提供的 OpenAPI"""

    _api_name = "bkiam"

    api = bind_property(Group, name="api")
