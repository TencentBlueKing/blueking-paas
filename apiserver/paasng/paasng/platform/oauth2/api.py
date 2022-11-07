# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import json
import logging
from contextlib import contextmanager

import requests
from django.conf import settings

from paasng.platform.oauth2.exceptions import BkOauthApiException, BkOauthApiResponseError, BkOauthClientDoesNotExist

logger = logging.getLogger(__name__)


@contextmanager
def wrap_request_exc():
    try:
        yield
    except requests.RequestException as e:
        logger.exception(f"unable to fetch response from {e.request.url}")
        raise BkOauthApiException(f'something wrong happened when fetching {e.request.url}') from e
    except json.decoder.JSONDecodeError as e:
        logger.exception(f'invalid json response: {e.doc}')
        raise BkOauthApiException(f'invalid json response: {e.doc}') from e
    except BkOauthApiResponseError as e:
        logger.exception(
            "invalid response(%s) from %s ,request_id: %s ,Detail: %s"
            % (e.status_code, e.request_url, e.request_id, e.response_text)
        )
        raise e


class BkOauthClient:
    def __init__(self):
        self.bk_oauth_url = settings.BK_OAUTH_API_URL.rstrip("/")
        self.headers = {"X-Bk-App-Code": settings.BK_APP_CODE, "X-Bk-App-Secret": settings.BK_APP_SECRET}

    @staticmethod
    def _validate_resp(resp: requests.Response):
        """Validate response status code"""
        if not (resp.status_code >= 200 and resp.status_code < 300):
            request_url = resp.request.url or ''
            raise BkOauthApiResponseError(
                f'stauts code is invalid: {resp.status_code}',
                status_code=resp.status_code,
                request_url=request_url,
                response_text=resp.text,
                request_id=resp.headers.get('x-request-id') or '',
            )

    def create_client(self, bk_app_code: str):
        """创建 oauth client"""
        url = f"{self.bk_oauth_url}/api/v1/apps"
        data = {
            "bk_app_code": bk_app_code,
            # oauth 未提供修改 name 的 API，name 也必须唯一，故 name 的值也是用 bk_app_code
            "name": bk_app_code,
        }
        with wrap_request_exc():
            resp = requests.post(url, json=data, headers=self.headers)
            # 状态码 409 代表 bk_app_code client 已经存在
            if resp.status_code == 200 or resp.status_code == 409:
                return

            self._validate_resp(resp)

    def get_client_secret(self, bk_app_code: str):
        """查询 oauth client key"""
        url = f"{self.bk_oauth_url}/api/v1/apps/{bk_app_code}/access-keys"
        with wrap_request_exc():
            resp = requests.get(url, headers=self.headers)

            # Oauth client 不存在抛出异常
            if resp.status_code == 404:
                raise BkOauthClientDoesNotExist(f"Bk Oauth client({bk_app_code}) not exist")

            self._validate_resp(resp)
            resp_data = resp.json()

            # 由于支持同一个app存在 2 个 secret, 所以返回的 secret 是一个列表
            access_keys = resp_data['data']
            # 默认取第一个
            return access_keys[0]['bk_app_secret']
