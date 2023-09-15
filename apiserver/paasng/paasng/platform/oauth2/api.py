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
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests
from django.conf import settings

import paasng.utils.masked_curlify as curlify
from paasng.platform.oauth2.exceptions import BkOauthApiException, BkOauthApiResponseError, BkOauthClientDoesNotExist

logger = logging.getLogger(__name__)


@dataclass
class BkAppSecret:
    id: int
    bk_app_code: str
    bk_app_secret: str
    enabled: bool
    created_at: datetime

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.strptime(self.created_at, "%Y-%m-%dT%H:%M:%SZ")  # type: ignore


@contextmanager
def wrap_request_exc():
    try:
        yield
    except requests.RequestException as e:
        logger.exception(f"unable to fetch response from {e.request.url}, curl: {curlify.to_curl(e.request)}")
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
            logger.error("request bkAuth api: %s", curlify.to_curl(resp.request))
            request_url = resp.request.url or ''
            raise BkOauthApiResponseError(
                f'stauts code is invalid: {resp.status_code}',
                status_code=resp.status_code,
                request_url=request_url,
                response_text=resp.text,
                request_id=resp.headers.get('x-request-id') or '',
            )

    def create_client(self, bk_app_code: str):
        """创建 OAuth 应用默认会生成对应的 bk_app_secret"""
        url = f"{self.bk_oauth_url}/api/v1/apps"
        data = {
            "bk_app_code": bk_app_code,
            # BKAuth 未提供修改 name 的 API，name 也必须唯一，故 name 的值也是用 bk_app_code
            "name": bk_app_code,
        }
        with wrap_request_exc():
            resp = requests.post(url, json=data, headers=self.headers)
            # 状态码 409 代表 bk_app_code client 已经存在
            if resp.status_code == 200 or resp.status_code == 409:
                return

            self._validate_resp(resp)

    def create_app_secret(self, bk_app_code: str):
        """同一个App最多拥有 2 个 bk_app_secret, 一般只有一个，两个主要是用于更换时，老的不会失效，除非管理方主动删除
        BkAuth API 会限制仅能创建 2 个 secret
        """
        url = f"{self.bk_oauth_url}/api/v1/apps/{bk_app_code}/access-keys"
        with wrap_request_exc():
            resp = requests.post(url, headers=self.headers)
            self._validate_resp(resp)
            return

    def del_app_secret(self, bk_app_code: str, bk_app_secret_id: int):
        """主要用于更换 bk_app_secret 后, 对老的 bk_app_secret进行删除, 若App只剩下唯一一个bk_app_secret, 则无法删除"""
        url = f"{self.bk_oauth_url}/api/v1/apps/{bk_app_code}/access-keys/{bk_app_secret_id}"
        with wrap_request_exc():
            resp = requests.delete(url, headers=self.headers)
            self._validate_resp(resp)
            return

    def toggle_app_secret(self, bk_app_code: str, bk_app_secret_id: int, enabled: bool):
        """禁用或启用应用 bk_app_secret"""
        url = f"{self.bk_oauth_url}/api/v1/apps/{bk_app_code}/access-keys/{bk_app_secret_id}"
        with wrap_request_exc():
            data = {"enabled": enabled}
            resp = requests.put(url, json=data, headers=self.headers)
            self._validate_resp(resp)
            return

    def get_app_secret_list(self, bk_app_code: str) -> List[BkAppSecret]:
        """查询应用 bk_app_secret 列表, 由于支持同一个应用存在2个 bk_app_secret, 所以返回的 bk_app_secret 是一个列表"""
        url = f"{self.bk_oauth_url}/api/v1/apps/{bk_app_code}/access-keys"
        with wrap_request_exc():
            resp = requests.get(url, headers=self.headers)

            # 应用 bk_app_secret 不存在抛出异常
            if resp.status_code == 404:
                raise BkOauthClientDoesNotExist(f"The bk_app_secret for the {bk_app_code} does not exist.")

            self._validate_resp(resp)
            resp_data = resp.json()['data']
            # 由于支持同一个app存在 2 个 secret, 所以返回的 secret 是一个列表
            return [
                BkAppSecret(d['id'], d['bk_app_code'], d['bk_app_secret'], d['enabled'], d['created_at'])
                for d in resp_data
            ]

    def get_default_app_secret(self, bk_app_code: str) -> BkAppSecret:
        """获取默认的密钥，应用有多个密钥时，按统一的规则获取一个默认的密钥。
        BkAuth 返回的多个 Secret 中，默认使用已启用且创建时间最早的
        """
        secret_list = self.get_app_secret_list(bk_app_code)

        # 只包含已启用（enabled 为 True）的 bk_app_secret,并按 created_at 升序排列
        filtered_data = [x for x in secret_list if x.enabled]
        if not filtered_data:
            raise BkOauthClientDoesNotExist(f"The bk_app_secret for the {bk_app_code} does not exist.")

        # 按 created_at 升序排列, 默认返回创建时间最早的
        sorted_data = sorted(filtered_data, key=lambda x: x.created_at, reverse=False)
        return sorted_data[0]

    def get_secret_by_id(self, bk_app_code: str, bk_app_secret_id: int) -> Optional[BkAppSecret]:
        """根据密钥 ID 查询密钥的详细信息"""
        secret_list = self.get_app_secret_list(bk_app_code)
        return next((x for x in secret_list if str(x.id) == str(bk_app_secret_id)), None)
