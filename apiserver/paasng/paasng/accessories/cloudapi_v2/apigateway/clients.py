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
from typing import Any

from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.accessories.cloudapi_v2.apigateway.apigw.clients import Client
from paasng.accessories.cloudapi_v2.apigateway.exceptions import ApiGatewayServiceError, ESBServiceError
from paasng.core.tenant.constants import API_HERDER_TENANT_ID

STAGE = settings.BK_API_DEFAULT_STAGE_MAPPINGS.get("bk-apigateway", "prod")


class ApiGatewayClient:
    """网关 API 通过 APIGW 提供的 API"""

    def __init__(self, tenant_id: str, bk_username: str):
        self.tenant_id = tenant_id
        self.bk_username = bk_username
        client = Client(endpoint=settings.BK_API_URL_TMPL_FOR_APIGW, stage=STAGE)
        client.update_headers(self._prepare_headers())
        self.client = client.api

    def _prepare_headers(self) -> dict:
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.BK_APP_CODE,
                    "bk_app_secret": settings.BK_APP_SECRET,
                    "bk_username": self.bk_username,
                }
            ),
            API_HERDER_TENANT_ID: self.tenant_id,
        }
        return headers

    # ============ 网关 API 相关 ============

    def list_gateways(self, name: str | None = None, fuzzy: bool = True) -> dict:
        """获取网关列表"""
        params = {}
        if name:
            params = {
                "name": name,
                "fuzzy": fuzzy,
            }

        try:
            res = self.client.list_gateways(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"list gateways error: {e}")

        return res.get("data", {})

    def get_gateway(self, gateway_name: str) -> dict:
        """获取单个网关详情"""
        try:
            res = self.client.get_gateway(path_params={"gateway_name": gateway_name})
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"get gateway error: {e}")

        return res.get("data", {})

    def list_gateway_permission_resources(
        self,
        app_code: str,
        gateway_name: str,
        keyword: str | None = None,
    ) -> dict:
        """获取网关资源列表（权限申请用）"""
        params: dict[str, Any] = {"target_app_code": app_code}
        if keyword:
            params["keyword"] = keyword

        try:
            res = self.client.list_gateway_permission_resources(
                params=params, path_params={"gateway_name": gateway_name}
            )
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"list gateway permission resources error: {e}")

        return res.get("data", {})

    def check_is_allowed_apply_by_gateway(self, app_code: str, gateway_name: str) -> dict:
        """是否允许按网关申请资源权限"""
        params: dict[str, Any] = {"target_app_code": app_code}

        try:
            res = self.client.check_is_allowed_apply_by_gateway(
                params=params, path_params={"gateway_name": gateway_name}
            )
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"check is allowed apply by gateway error: {e}")

        return res.get("data", {})

    def apply_gateway_resource_permission(
        self,
        app_code: str,
        gateway_name: str,
        resource_ids: list[int] | None = None,
        reason: str = "",
        expire_days: int = 0,
        grant_dimension: str = "resource",
    ) -> dict:
        """网关资源权限申请"""
        data: dict[str, Any] = {
            "target_app_code": app_code,
            "reason": reason,
            "expire_days": expire_days,
            "grant_dimension": grant_dimension,
        }
        if resource_ids:
            data["resource_ids"] = resource_ids

        try:
            res = self.client.apply_gateway_resource_permission(data=data, path_params={"gateway_name": gateway_name})
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"apply gateway resource permission error: {e}")

        return res.get("data", {})

    def list_app_resource_permissions(self, app_code: str) -> dict:
        """已申请的资源权限列表"""
        params: dict[str, Any] = {"target_app_code": app_code}

        try:
            res = self.client.list_app_resource_permissions(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"list app resource permissions error: {e}")

        return res.get("data", {})

    def renew_resource_permission(
        self,
        app_code: str,
        resource_ids: list[int],
        expire_days: int,
    ) -> str:
        """权限续期"""
        data: dict[str, Any] = {
            "target_app_code": app_code,
            "resource_ids": resource_ids,
            "expire_days": expire_days,
        }

        try:
            res = self.client.renew_resource_permission(data=data)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"renew resource permission error: {e}")

        # 这里网关正常会响应 204 No Content, 故不能取 data
        return res

    def list_resource_permission_apply_records(self, app_code: str, **kwargs) -> dict:
        """资源权限申请记录列表"""
        params: dict[str, Any] = {"target_app_code": app_code}
        params.update(kwargs)

        try:
            res = self.client.list_resource_permission_apply_records(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"list resource permission apply records error: {e}")

        return res.get("data", {})

    def retrieve_resource_permission_apply_record(self, app_code: str, record_id: int) -> dict:
        """资源权限申请记录详情"""
        params: dict[str, Any] = {"target_app_code": app_code}

        try:
            res = self.client.retrieve_resource_permission_apply_record(
                params=params, path_params={"record_id": record_id}
            )
        except (APIGatewayResponseError, ResponseError) as e:
            raise ApiGatewayServiceError(f"retrieve resource permission apply record error: {e}")

        return res.get("data", {})

    def list_esb_systems(self, user_auth_type: str) -> dict:
        """查询组件系统列表"""
        params = {"user_auth_type": user_auth_type}
        try:
            res = self.client.list_esb_systems(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"list esb systems error: {e}")

        return res.get("data", {})

    def list_esb_system_permission_components(
        self,
        app_code: str,
        system_id: int,
        keyword: str | None = None,
    ) -> dict:
        """查询系统权限组件"""
        params: dict[str, Any] = {"target_app_code": app_code}
        if keyword:
            params["keyword"] = keyword

        try:
            res = self.client.list_esb_system_permission_components(
                params=params, path_params={"system_id": system_id}
            )
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"list esb system permission components error: {e}")

        return res.get("data", {})

    def apply_esb_system_component_permissions(
        self,
        app_code: str,
        system_id: int,
        component_ids: list[int],
        reason: str = "",
        expire_days: int = 0,
    ) -> dict:
        """创建申请 ESB 组件权限的申请单据"""
        data: dict[str, Any] = {
            "target_app_code": app_code,
            "component_ids": component_ids,
            "reason": reason,
            "expire_days": expire_days,
        }

        try:
            res = self.client.apply_esb_system_component_permissions(data=data, path_params={"system_id": system_id})
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"apply esb system component permissions error: {e}")

        return res.get("data", {})

    def renew_esb_component_permissions(
        self,
        app_code: str,
        component_ids: list[int],
        expire_days: int,
    ) -> str:
        """ESB 组件权限续期"""
        data: dict[str, Any] = {
            "target_app_code": app_code,
            "component_ids": component_ids,
            "expire_days": expire_days,
        }

        try:
            res = self.client.renew_esb_component_permissions(data=data)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"renew esb component permissions error: {e}")

        # 这里网关正常会响应 204 No Content
        return res

    def list_app_esb_component_permissions(self, app_code: str) -> dict:
        """已申请的 ESB 组件权限列表"""
        params: dict[str, Any] = {"target_app_code": app_code}

        try:
            res = self.client.list_app_esb_component_permissions(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"list app esb component permissions error: {e}")

        return res.get("data", {})

    def list_app_esb_component_permission_apply_records(self, app_code: str, **kwargs) -> dict:
        """查询应用权限申请记录列表"""
        params: dict[str, Any] = {"target_app_code": app_code}
        params.update(kwargs)

        try:
            res = self.client.list_app_esb_component_permission_apply_records(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"list app esb component permission apply records error: {e}")

        return res.get("data", {})

    def get_app_esb_component_permission_apply_record(self, app_code: str, record_id: int) -> dict:
        """查询应用权限申请记录详情"""
        params: dict[str, Any] = {"target_app_code": app_code}

        try:
            res = self.client.get_app_esb_component_permission_apply_record(
                params=params, path_params={"record_id": record_id}
            )
        except (APIGatewayResponseError, ResponseError) as e:
            raise ESBServiceError(f"get app esb component permission apply record error: {e}")

        return res.get("data", {})
