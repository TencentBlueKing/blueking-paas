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

from django.conf import settings
from django.utils.translation import get_language

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.utils.error_codes import error_codes

from .component import BaseComponent
from .http import http_get, http_post

# bk-apigateway 接口地址
BK_APIGATEWAY_V2_GATEWAY_STAGE = settings.BK_API_V2_DEFAULT_STAGE_MAPPINGS.get("bk-apigateway", "prod")
BK_APIGATEWAY_V2_API_URL = (
    f"{settings.BK_API_V2_URL_TMPL.format(api_name='bk-apigateway').rstrip('/')}/{BK_APIGATEWAY_V2_GATEWAY_STAGE}"
)


class BkApigatewayV2Component(BaseComponent):
    host = BK_APIGATEWAY_V2_API_URL
    system_name = "bk-apigateway"

    def get(self, path: str, tenant_id: str, bk_username: str = "", **kwargs):
        return self._call_api(http_get, path, headers=self._prepare_headers(bk_username, tenant_id), **kwargs)

    def post(self, path: str, tenant_id: str, bk_username: str = "", **kwargs):
        return self._call_api(http_post, path, headers=self._prepare_headers(bk_username, tenant_id), **kwargs)

    def _call_api(self, http_func, path: str, **kwargs) -> Any:
        """覆写，apigw v2 不再返回 code，删除 code 的校验"""
        url = self._urljoin(self.host, path)
        http_ok, resp_data = http_func(url, **kwargs)

        if not (http_ok and resp_data):
            raise error_codes.REMOTE_REQUEST_ERROR.format(f"request {self.system_name} api error")

        return resp_data

    def _prepare_headers(self, bk_username: str, tenant_id: str):
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.BK_APP_CODE,
                    "bk_app_secret": settings.BK_APP_SECRET,
                    "bk_username": bk_username,
                }
            ),
            API_HERDER_TENANT_ID: tenant_id,
        }

        language = get_language()
        if language:
            headers["Accept-Language"] = language

        return headers


bk_apigateway_v2_component = BkApigatewayV2Component()
