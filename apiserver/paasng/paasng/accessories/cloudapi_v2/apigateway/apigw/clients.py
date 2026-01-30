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

import json

from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property
from bkapi_client_core.client import ResponseHeadersRepresenter
from bkapi_client_core.exceptions import (
    HTTPResponseError,
)
from requests import Response
from requests.exceptions import HTTPError


class Group(OperationGroup):
    # ============ 网关 API 相关 ============

    # 获取网关列表
    list_gateways = bind_property(
        Operation,
        name="list_gateways",
        method="GET",
        path="/api/v2/inner/gateways/",
    )

    # 获取单个网关详情
    get_gateway = bind_property(
        Operation,
        name="get_gateway",
        method="GET",
        path="/api/v2/inner/gateways/{gateway_name}/",
    )

    # 获取网关资源列表（权限申请用）
    list_gateway_permission_resources = bind_property(
        Operation,
        name="list_gateway_permission_resources",
        method="GET",
        path="/api/v2/inner/gateways/{gateway_name}/permissions/resources/",
    )

    # 是否允许按网关申请资源权限
    check_is_allowed_apply_by_gateway = bind_property(
        Operation,
        name="check_is_allowed_apply_by_gateway",
        method="GET",
        path="/api/v2/inner/gateways/{gateway_name}/permissions/app-permissions/allow-apply-by-gateway/",
    )

    # 网关资源权限申请
    apply_gateway_resource_permission = bind_property(
        Operation,
        name="apply_gateway_resource_permission",
        method="POST",
        path="/api/v2/inner/gateways/{gateway_name}/permissions/app-permissions/apply/",
    )

    # 已申请的资源权限列表
    list_app_resource_permissions = bind_property(
        Operation,
        name="list_app_resource_permissions",
        method="GET",
        path="/api/v2/inner/gateways/permissions/app-permissions/",
    )

    # 权限续期
    renew_resource_permission = bind_property(
        Operation,
        name="renew_resource_permission",
        method="POST",
        path="/api/v2/inner/gateways/permissions/renew/",
    )

    # 资源权限申请记录列表
    list_resource_permission_apply_records = bind_property(
        Operation,
        name="list_resource_permission_apply_records",
        method="GET",
        path="/api/v2/inner/gateways/permissions/apply-records/",
    )

    # 资源权限申请记录详情
    retrieve_resource_permission_apply_record = bind_property(
        Operation,
        name="retrieve_resource_permission_apply_record",
        method="GET",
        path="/api/v2/inner/gateways/permissions/apply-records/{record_id}/",
    )

    # ============ ESB 组件 API 相关 ============

    # 查询组件系统列表
    list_esb_systems = bind_property(
        Operation,
        name="list_esb_systems",
        method="GET",
        path="/api/v2/inner/esb/systems/",
    )

    # 查询系统权限组件
    list_esb_system_permission_components = bind_property(
        Operation,
        name="list_esb_system_permission_components",
        method="GET",
        path="/api/v2/inner/esb/systems/{system_id}/permissions/components/",
    )

    # 创建申请 ESB 组件权限的申请单据
    apply_esb_system_component_permissions = bind_property(
        Operation,
        name="apply_esb_system_component_permissions",
        method="POST",
        path="/api/v2/inner/esb/systems/{system_id}/permissions/apply/",
    )

    # ESB 组件权限续期
    renew_esb_component_permissions = bind_property(
        Operation,
        name="renew_esb_component_permissions",
        method="POST",
        path="/api/v2/inner/esb/systems/permissions/renew/",
    )

    # 已申请的 ESB 组件权限列表
    list_app_esb_component_permissions = bind_property(
        Operation,
        name="list_app_esb_component_permissions",
        method="GET",
        path="/api/v2/inner/esb/systems/permissions/app-permissions/",
    )

    # 查询应用权限申请记录列表
    list_app_esb_component_permission_apply_records = bind_property(
        Operation,
        name="list_app_esb_component_permission_apply_records",
        method="GET",
        path="/api/v2/inner/esb/systems/permissions/apply-records/",
    )

    # 查询应用权限申请记录详情
    get_app_esb_component_permission_apply_record = bind_property(
        Operation,
        name="get_app_esb_component_permission_apply_record",
        method="GET",
        path="/api/v2/inner/esb/systems/permissions/apply-records/{record_id}/",
    )


class Client(APIGatewayClient):
    """bk-apigateway client"""

    _api_name = "bk-apigateway"

    api = bind_property(Group, name="api")

    def _handle_response_content(
        self,
        operation: Operation,
        response: Response | None,
    ):
        # 覆写父类方法, 接受非 JSON 类型的响应 对应网关 v2 响应格式
        if response is None:
            return None

        self.check_response_apigateway_error(response)

        try:
            response.raise_for_status()
        except HTTPError as err:
            response_headers_representer = ResponseHeadersRepresenter(response.headers)
            raise HTTPResponseError(
                "Error responded by Backend api, %s" % str(err),
                response=response,
                response_headers_representer=response_headers_representer,
            )

        try:
            return response.json()
        except (TypeError, json.JSONDecodeError):
            return response.text
