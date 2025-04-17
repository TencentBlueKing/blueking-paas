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
import logging

from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.bk_plugins.pluginscenter.bk_aidev.apigw.client import Client
from paasng.bk_plugins.pluginscenter.bk_aidev.exceptions import BkAiDevApiError, BkAiDevGatewayServiceError
from paasng.core.tenant.constants import API_HERDER_TENANT_ID

logger = logging.getLogger(__name__)


class BkAiDevClient:
    """bk-aidev 通过 APIGW 提供的 API"""

    def __init__(self, login_cookie: str, tenant_id: str):
        self.login_cookie_name = settings.BK_COOKIE_NAME
        self.login_cookie = login_cookie
        self.tenant_id = tenant_id
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage="prod")
        client.update_headers(self._prepare_headers())
        self.client = client.api

    def _prepare_headers(self) -> dict:
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.BK_APP_CODE,
                    "bk_app_secret": settings.BK_APP_SECRET,
                    self.login_cookie_name: self.login_cookie,
                }
            ),
            API_HERDER_TENANT_ID: self.tenant_id,
        }
        return headers

    def list_spaces(self) -> list:
        """获取空间列表"""
        try:
            res = self.client.list_user_mode_resource_meta_user_spaces()
        except (APIGatewayResponseError, ResponseError) as e:
            logger.exception("list ai-dev spaces failed")
            raise BkAiDevGatewayServiceError(f"list ai-dev spaces error: {e}")

        # 返回的数据格式为：{'result': True, 'code': 'success', 'message': None, 'data': [{'space_id': '6f1c831bfcb52b9a', 'space_name': 'cloud4paas', 'space_desc': None}]
        if res.get("result"):
            return res.get("data", [])
        else:
            raise BkAiDevApiError(f"list ai-dev spaces error: {res.get('message')}")
