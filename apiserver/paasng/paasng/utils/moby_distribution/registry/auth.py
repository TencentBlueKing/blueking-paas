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

import base64
import logging
from typing import Any, Dict, Optional

import requests
from www_authenticate import parse

from paasng.utils.moby_distribution.registry.exceptions import AuthFailed
from paasng.utils.moby_distribution.registry.utils import TypeTimeout
from paasng.utils.moby_distribution.spec.auth import TokenResponse

AUTH_TIMEOUT = 30
logger = logging.getLogger(__name__)


class AuthorizationProvider:
    def provide(self) -> str:
        """Provide the 'Authorization' used in HTTP Headers

        Usage: AuthorizationProvider().provider()
        """
        raise NotImplementedError


class BaseAuthentication:
    """Base Authentication Protocol"""

    def __init__(self, www_authenticate: str):
        self._raw_www_authenticate = www_authenticate
        self._www_authenticate = None

    @property
    def www_authenticate(self):
        if self._www_authenticate is None:
            self._www_authenticate = parse(self._raw_www_authenticate)
        return self._www_authenticate

    def authenticate(
        self, username: Optional[str] = None, password: Optional[str] = None, *, timeout: TypeTimeout = AUTH_TIMEOUT
    ) -> AuthorizationProvider:
        raise NotImplementedError

    @property
    def raw_www_authenticate(self) -> str:
        return self._raw_www_authenticate


class BasicAuthAuthorizationProvider(AuthorizationProvider):
    """BasicAuthAuthorizationProvider provide the `HTTP Basic Authentication`"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def provide(self) -> str:
        auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return f"Basic {auth}"


class TokenAuthorizationProvider(AuthorizationProvider):
    """TokenAuthorizationProvider provide the `Bearer Token` Authentication"""

    def __init__(self, token_response: TokenResponse, token_type: str = "Bearer"):
        self.token_response = token_response
        self.token_type = token_type

    def provide(self) -> str:
        if self.token_response.token:
            return f"{self.token_type} {self.token_response.token}"
        elif self.token_response.access_token:
            return f"{self.token_type} {self.token_response.access_token}"
        raise ValueError("Missing Token")


class HTTPBasicAuthentication(BaseAuthentication):
    """`HTTP Basic Authentication` Authenticator"""

    def authenticate(
        self, username: Optional[str] = None, password: Optional[str] = None, *, timeout: TypeTimeout = AUTH_TIMEOUT
    ) -> AuthorizationProvider:
        if username is None or password is None:
            raise AuthFailed(
                message="请提供用户名和密码",
                status_code=400,
                response=None,
            )
        return BasicAuthAuthorizationProvider(username, password)


class DockerRegistryTokenAuthentication(BaseAuthentication):
    """Docker Registry v2 authentication via central service

    spec: https://github.com/distribution/distribution/blob/main/docs/spec/auth/token.md
    """

    REQUIRE_KEYS = ["realm", "service"]
    backend: str
    service: str
    scope: str

    def __init__(self, www_authenticate: str, offline_token: bool = True):
        super().__init__(www_authenticate)
        self.offline_token = offline_token

        assert "bearer" in self.www_authenticate
        self.bearer = self.www_authenticate["bearer"]

        for key in self.REQUIRE_KEYS:
            assert key in self.bearer

        self.backend = self.bearer["realm"]
        self.service = self.bearer["service"]
        self.scope = self.bearer.get("scope", None)

    def authenticate(
        self, username: Optional[str] = None, password: Optional[str] = None, *, timeout: TypeTimeout = AUTH_TIMEOUT
    ) -> AuthorizationProvider:
        """Authenticate to the registry.
        If no username and password provided, will authenticate as the anonymous user.

        :param username: User name to authenticate as.
        :param password: User's password.
        :return:
        """
        params: Dict[str, Any] = {
            "service": self.service,
            "scope": self.scope,
            "client_id": username or "anonymous",
            "offline_token": self.offline_token,
        }
        headers = {}
        if username and password:
            auth = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"
        elif any([username, password]) and not all([username, password]):
            logger.warning("请同时提供 username 和 password!")

        logger.info("sending authentication request to authorization service<%s>", self.backend)
        resp = requests.get(self.backend, headers=headers, params=params, timeout=timeout)
        if resp.status_code != 200:
            raise AuthFailed(
                message="用户凭证校验失败, 请检查用户信息和操作权限",
                status_code=resp.status_code,
                response=resp,
            )
        return TokenAuthorizationProvider(TokenResponse(**resp.json()))


class UniversalAuthentication(BaseAuthentication):
    """An Auto auth backend, which will auto auth by `scheme` provided by www_authenticate"""

    def authenticate(
        self, username: Optional[str] = None, password: Optional[str] = None, *, timeout: TypeTimeout = AUTH_TIMEOUT
    ) -> AuthorizationProvider:
        if "basic" in self.www_authenticate:
            return HTTPBasicAuthentication(self.raw_www_authenticate).authenticate(username, password, timeout=timeout)
        elif "bearer" in self.www_authenticate:
            return DockerRegistryTokenAuthentication(self.raw_www_authenticate).authenticate(
                username, password, timeout=timeout
            )
        raise NotImplementedError("未支持的认证方式")
