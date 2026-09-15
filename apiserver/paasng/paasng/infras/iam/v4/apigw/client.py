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
