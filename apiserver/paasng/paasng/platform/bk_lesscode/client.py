# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
import json
import logging
from typing import Optional

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from django.utils.translation import get_language

from paasng.platform.bk_lesscode.apigw.client import Client
from paasng.platform.bk_lesscode.apigw.client import Group as LessCodeGroup
from paasng.platform.bk_lesscode.exceptions import LessCodeApiError, LessCodeGatewayServiceError

logger = logging.getLogger(__name__)


class DummyLessCodeClient:
    def create_app(self, app_id: str, app_name: str, module_name: str) -> bool:
        return True

    def get_address(self, app_id: str, module_name: str) -> str:
        return ""


class LessCodeClient:
    """bk_lesscode 通过 APIGW 提供的 API"""

    def __init__(self, login_cookie: str, client: Optional[LessCodeGroup] = None):
        self.client = client or self._make_api_client()
        self.login_cookie_name = settings.BK_COOKIE_NAME
        self.login_cookie = login_cookie

    def _make_api_client(self) -> LessCodeGroup:
        """Make a client object for requesting"""
        return Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_PLUGIN_APIGW_SERVICE_STAGE).api

    def _prepare_headers(self) -> dict:
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.BK_APP_CODE,
                    "bk_app_secret": settings.BK_APP_SECRET,
                    self.login_cookie_name: self.login_cookie,
                }
            )
        }

        # 需要 lesscode 的 API 支持国际化
        language = get_language()
        if language:
            headers["Accept-Language"] = language

        return headers

    def create_app(self, app_id: str, app_name: str, module_name: str) -> bool:
        """在 lesscode 平台上创建应用,lesscode 侧应用的 ID 为 "{app_id}/{module_name}" """
        data = {"appCode": app_id, "appName": app_name, "moduleCode": module_name}
        try:
            resp = self.client.create_project_by_app(
                headers=self._prepare_headers(),
                data=data,
            )
        except APIGatewayResponseError as e:
            # bkapi_client sdk 中已经记录了详细的日志，这里就不需要再记录
            raise LessCodeGatewayServiceError(f"create lesscode app error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(f'create lesscode app error, message:{resp["message"]} \n data: {data}')
            raise LessCodeApiError(resp["message"])

        return True

    def get_address(self, app_id: str, module_name: str) -> str:
        """获取模块在 lesscode 平台上的访问地址, 因为私有化部署时 lesscode 平台也不知道自己的域名，所以只返回路径"""

        params = {"appCode": app_id, "moduleCode": module_name}
        try:
            resp = self.client.find_project_by_app(headers=self._prepare_headers(), params=params)
        except Exception as e:
            logger.exception(f"get lesscode app address path, detail: {e}")
            # 获取不到地址时，不展示给用户就行，页面上不需要报错
            return ""

        if resp.get("code") != 0:
            logger.exception(f'create lesscode app error, message:{resp["message"]} \n params: {params}')
            return ""

        address_path = resp.get("data", {}).get("linkUrl")
        return f"{settings.BK_LESSCODE_URL}{address_path}"


def make_bk_lesscode_client(login_cookie: str, client: Optional[LessCodeGroup] = None):
    if settings.ENABLE_BK_LESSCODE_APIGW:
        return LessCodeClient(login_cookie, client)
    else:
        return DummyLessCodeClient()
