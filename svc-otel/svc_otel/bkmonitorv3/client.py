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

import logging
from typing import Dict, Optional

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from typing_extensions import Protocol

from svc_otel.bkmonitorv3.backend.apigw import Client
from svc_otel.bkmonitorv3.backend.esb import get_client_by_username
from svc_otel.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError

logger = logging.getLogger(__name__)


class BkMonitorBackend(Protocol):
    """Describes protocols of calling API service"""

    def apm_create_application(self, *args, **kwargs) -> Dict: ...

    def detail_apm_application(self, *args, **kwargs) -> Dict: ...


class BkMonitorClient:
    """API provided by BK Monitor

    :param backend: client 后端实际的 backend
    """

    def __init__(
        self,
        backend: BkMonitorBackend,
    ):
        self.client = backend

    def get_apm(self, apm_name: str, bk_monitor_space_id: str) -> Optional[str]:
        """查询 APM 应用详情，存在则返回 data_token，不存在返回 None

        文档: GET /app/apm/detail_apm_application/
        传参三选一：application_id，或 bk_biz_id + app_name，或 space_uid + app_name
        """
        data = {"app_name": apm_name, "space_uid": bk_monitor_space_id}
        try:
            resp = self.client.detail_apm_application(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError("Failed to get APM on BK Monitor") from e

        if not resp.get("result"):
            logger.info(
                "APM application not found on BK Monitor, resp: %s, apm_name: %s, space_uid: %s",
                resp,
                apm_name,
                bk_monitor_space_id,
            )
            return None

        token = (resp.get("data") or {}).get("token")
        if not token:
            logger.error(
                "APM application found but token is empty, resp: %s, apm_name: %s, space_uid: %s",
                resp,
                apm_name,
                bk_monitor_space_id,
            )
            raise BkMonitorApiError("APM application token is empty")
        return token

    def create_apm(self, apm_name: str, bk_monitor_space_id: str) -> str:
        """创建 APM 应用，返回 data_token

        OTEL 的返回数据格式：
        {
            "result": true,
            "code": 200,
            "message": "OK",
            "data": "xxxxxxx",
            "request_id": "d29570cab0d447529d53cc192df25157"
        }

        {
            "result": false,
            "message": "应用名称已存在",
            "data": {},
            "code": 500,
            "request_id": "a06f6c1a66c34d0a880186759fec0d06"
        }
        """
        # 在指定的命名空间下创建 APM 应用
        data = {"app_name": apm_name, "space_uid": bk_monitor_space_id}
        try:
            resp = self.client.apm_create_application(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError("Failed to create APM on BK Monitor") from e

        if not resp["result"]:
            logger.error(
                f"Failed to create APM on BK Monitor, resp: {resp}, apm_name: {apm_name}, space_uid: {bk_monitor_space_id}"
            )
            raise BkMonitorApiError(resp["message"])
        return resp["data"]

    def get_or_create_apm(self, apm_name: str, bk_monitor_space_id: str) -> str:
        """先查 APM 应用，不存在再创建，返回 data_token"""
        data_token = self.get_apm(apm_name, bk_monitor_space_id)
        if data_token:
            return data_token

        try:
            return self.create_apm(apm_name, bk_monitor_space_id)
        except BkMonitorApiError as e:
            # 并发创建时可能已经存在，再查一次
            if "已存在" not in str(e):
                raise
            data_token = self.get_apm(apm_name, bk_monitor_space_id)
            if data_token:
                return data_token
            raise


def make_bk_monitor_client(tenant_id) -> BkMonitorClient:
    if settings.ENABLE_BK_MONITOR_APIGW:
        apigw_client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.APIGW_ENVIRONMENT)
        apigw_client.update_bkapi_authorization(bk_app_code=settings.BK_APP_CODE, bk_app_secret=settings.BK_APP_SECRET)
        apigw_client.update_headers(
            {
                "X-Bk-Tenant-Id": tenant_id,
            }
        )
        return BkMonitorClient(apigw_client.api)

    # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
    esb_client = get_client_by_username("admin")
    return BkMonitorClient(esb_client.monitor_v3)
