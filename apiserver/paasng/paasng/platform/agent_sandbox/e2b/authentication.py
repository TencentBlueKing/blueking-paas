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

"""e2b 协议路由专用的认证后端。

只挂在 e2b 兼容端点上，不进 ``DEFAULT_AUTHENTICATION_CLASSES``，
因此 apiserver 既有接口的认证方式不受影响。
"""

from dataclasses import dataclass

from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from paasng.platform.agent_sandbox.models import E2BApiKey

from .constants import API_KEY_HEADER
from .keys import hash_api_key, is_well_formed

# key 无效、已吊销、格式非法三种情况共用这一句，避免调用方通过错误信息区分
_AUTH_FAILED_MESSAGE = "Invalid API key"


@dataclass
class E2BPrincipal:
    """通过 API Key 认证后的请求主体。

    充当 DRF 的 ``request.user``，因此需要 ``is_authenticated``，
    这样 ``IsAuthenticated`` 之类的通用权限类仍然可用。
    """

    api_key: E2BApiKey

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def application(self):
        return self.api_key.application

    @property
    def tenant_id(self) -> str:
        return self.api_key.tenant_id

    def __str__(self) -> str:
        return f"e2b:{self.api_key.key_prefix}"


class E2BApiKeyAuthentication(authentication.BaseAuthentication):
    """校验 ``X-API-Key``，把归属主体注入 ``request.user``。"""

    def authenticate(self, request):
        raw_key = request.META.get("HTTP_X_API_KEY", "")
        if not raw_key:
            raise AuthenticationFailed(_AUTH_FAILED_MESSAGE)

        # 格式不合法的 key 不可能在库里，先挡掉省一次查询
        if not is_well_formed(raw_key):
            raise AuthenticationFailed(_AUTH_FAILED_MESSAGE)

        api_key = E2BApiKey.objects.filter(key_hash=hash_api_key(raw_key), enabled=True).first()
        if api_key is None:
            raise AuthenticationFailed(_AUTH_FAILED_MESSAGE)

        return E2BPrincipal(api_key=api_key), api_key

    def authenticate_header(self, request):
        """返回 ``WWW-Authenticate`` 头，让 DRF 用 401 而不是 403 响应未认证请求。"""
        return API_KEY_HEADER
