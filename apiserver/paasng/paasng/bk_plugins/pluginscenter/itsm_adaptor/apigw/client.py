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

from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property


class Group(OperationGroup):
    # 单据关注取关接口
    add_follower = bind_property(
        Operation,
        name="add_follower",
        method="POST",
        path="/v2/itsm/add_follower/",
    )

    # 对单据某个审批节点进行审批操作
    approve = bind_property(
        Operation,
        name="approve",
        method="POST",
        path="/v2/itsm/approve/",
    )

    # 回调失败的单据
    callback_failed_ticket = bind_property(
        Operation,
        name="callback_failed_ticket",
        method="GET",
        path="/v2/itsm/callback_failed_ticket/",
    )

    # 创建服务目录
    create_service_catalog = bind_property(
        Operation,
        name="create_service_catalog",
        method="POST",
        path="/v2/itsm/create_service_catalog/",
    )

    # 创建单据
    create_ticket = bind_property(
        Operation,
        name="create_ticket",
        method="POST",
        path="/v2/itsm/create_ticket/",
    )

    # 获取当前单据指定节点的审批人
    get_approver = bind_property(
        Operation,
        name="get_approver",
        method="GET",
        path="/v2/itsm/get_approver/",
    )

    # 服务目录查询
    get_service_catalogs = bind_property(
        Operation,
        name="get_service_catalogs",
        method="GET",
        path="/v2/itsm/get_service_catalogs/",
    )

    # 服务详情查询
    get_service_detail = bind_property(
        Operation,
        name="get_service_detail",
        method="GET",
        path="/v2/itsm/get_service_detail/",
    )

    # 服务角色查询
    get_service_roles = bind_property(
        Operation,
        name="get_service_roles",
        method="GET",
        path="/v2/itsm/get_service_roles/",
    )

    # 服务列表查询
    get_services = bind_property(
        Operation,
        name="get_services",
        method="GET",
        path="/v2/itsm/get_services/",
    )

    # 单据详情查询
    get_ticket_info = bind_property(
        Operation,
        name="get_ticket_info",
        method="GET",
        path="/v2/itsm/get_ticket_info/",
    )

    # 单据日志查询
    get_ticket_logs = bind_property(
        Operation,
        name="get_ticket_logs",
        method="GET",
        path="/v2/itsm/get_ticket_logs/",
    )

    # 单据状态查询
    get_ticket_status = bind_property(
        Operation,
        name="get_ticket_status",
        method="GET",
        path="/v2/itsm/get_ticket_status/",
    )

    # 获取单据列表
    get_tickets = bind_property(
        Operation,
        name="get_tickets",
        method="POST",
        path="/v2/itsm/get_tickets/",
    )

    # 通过用户获取单据
    get_tickets_by_user = bind_property(
        Operation,
        name="get_tickets_by_user",
        method="GET",
        path="/v2/itsm/get_tickets_by_user/",
    )

    # 获取流程详情
    get_workflow_detail = bind_property(
        Operation,
        name="get_workflow_detail",
        method="GET",
        path="/v2/itsm/get_workflow_detail",
    )

    # 导入服务
    import_service = bind_property(
        Operation,
        name="import_service",
        method="POST",
        path="/v2/itsm/import_service/",
    )

    # 处理单据节点
    operate_node = bind_property(
        Operation,
        name="operate_node",
        method="POST",
        path="/v2/itsm/operate_node/",
    )

    # 处理单据
    operate_ticket = bind_property(
        Operation,
        name="operate_ticket",
        method="POST",
        path="/v2/itsm/operate_ticket/",
    )

    # 审批节点处理
    proceed_approval = bind_property(
        Operation,
        name="proceed_approval",
        method="POST",
        path="/v2/itsm/proceed_approval/",
    )

    # 查询审批结果
    ticket_approval_result = bind_property(
        Operation,
        name="ticket_approval_result",
        method="POST",
        path="/v2/itsm/ticket_approval_result/",
    )

    # token校验
    token_verify = bind_property(
        Operation,
        name="token_verify",
        method="POST",
        path="/v2/itsm/token/verify/",
    )

    # 更新某个服务
    update_service = bind_property(
        Operation,
        name="update_service",
        method="POST",
        path="/v2/itsm/update_service/",
    )


class Client(APIGatewayClient):
    """bk-itsm
    工单流系统
    """

    _api_name = "bk-itsm"

    api = bind_property(Group, name="api")
