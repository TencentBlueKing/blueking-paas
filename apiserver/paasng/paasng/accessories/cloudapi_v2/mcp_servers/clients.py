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

import json

from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings
from requests.exceptions import RequestException

from paasng.accessories.cloudapi_v2.apply_records import ApplyRecordOperateError
from paasng.accessories.cloudapi_v2.mcp_servers.apigw.clients import Client
from paasng.accessories.cloudapi_v2.mcp_servers.exceptions import MCPServerApiGatewayServiceError
from paasng.core.tenant.constants import API_HERDER_TENANT_ID

STAGE = settings.BK_API_DEFAULT_STAGE_MAPPINGS.get("bk-apigateway", "prod")


class MCPServerApiClient:
    """mcp server api 通过 APIGW 提供的 API"""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        client = Client(endpoint=settings.BK_API_URL_TMPL_FOR_APIGW, stage=STAGE)
        client.update_headers(self._prepare_headers())
        self.client = client.api

    def _prepare_headers(self) -> dict:
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.BK_APP_CODE,
                    "bk_app_secret": settings.BK_APP_SECRET,
                }
            ),
            API_HERDER_TENANT_ID: self.tenant_id,
        }
        return headers

    def list_app_mcp_servers(self, app_code: str, keyword: str | None = None) -> dict:
        """获取 mcp server 列表"""
        params = {"target_app_code": app_code}
        if keyword:
            params["keyword"] = keyword

        try:
            res = self.client.list_app_mcp_servers(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise MCPServerApiGatewayServiceError(f"list mcp servers error: {e}")

        return res.get("data", {})

    def list_app_permissions(self, app_code: str) -> dict:
        """获取应用的 mcp server 权限列表"""

        try:
            res = self.client.list_app_permissions(params={"target_app_code": app_code})
        except (APIGatewayResponseError, ResponseError) as e:
            raise MCPServerApiGatewayServiceError(f"list app permissions error: {e}")
        return res.get("data", {})

    def list_permissions_apply_records(
        self,
        app_code: str,
        applied_by: str | None = None,
        applied_time_start: int | None = None,
        applied_time_end: int | None = None,
        apply_status: str | None = None,
        query: str | None = None,
    ) -> dict:
        """获取应用权限申请记录列表"""
        params = {"target_app_code": app_code}
        if applied_by:
            params["applied_by"] = applied_by
        if applied_time_start:
            params["applied_time_start"] = applied_time_start  # type: ignore
        if applied_time_end:
            params["applied_time_end"] = applied_time_end  # type: ignore
        if apply_status:
            params["apply_status"] = apply_status
        if query:
            params["query"] = query

        try:
            res = self.client.list_permissions_apply_records(params=params)
        except (APIGatewayResponseError, ResponseError) as e:
            raise MCPServerApiGatewayServiceError(f"list permissions apply records error: {e}")

        return res.get("data", {})

    def apply_permissions(
        self,
        app_code: str,
        mcp_server_ids: list,
        applied_by: str,
        reason: str,
    ):
        """申请 mcp server 权限"""
        data = {
            "target_app_code": app_code,
            "mcp_server_ids": mcp_server_ids,
            "applied_by": applied_by,
            "reason": reason,
        }
        try:
            self.client.apply_permissions(data=data)
        except (APIGatewayResponseError, ResponseError) as e:
            raise MCPServerApiGatewayServiceError(f"apply permissions error: {e}")

    def cancel_permission_apply_record(self, app_code: str, record_id: int, operated_by: str) -> None:
        """取消待审批的 MCP Server 权限申请"""
        data = {"target_app_code": app_code, "operated_by": operated_by}

        try:
            self.client.cancel_permission_apply_record(data=data, path_params={"record_id": record_id})
        except RequestException as e:
            raise ApplyRecordOperateError.from_exception(e) from e

    def delete_permission_apply_record(self, app_code: str, record_id: int, operated_by: str) -> None:
        """删除已取消的 MCP Server 权限申请"""
        params = {"target_app_code": app_code, "operated_by": operated_by}

        try:
            self.client.delete_permission_apply_record(params=params, path_params={"record_id": record_id})
        except RequestException as e:
            raise ApplyRecordOperateError.from_exception(e) from e
