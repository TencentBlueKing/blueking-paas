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

# we have to enable http for paasng site
# which is not allowed by default in Oauth2
import logging
import os
from typing import ClassVar, Dict, List

import cattr
import requests
from attrs import define, evolve, field
from django.conf import settings
from requests.models import Response
from requests_oauthlib import OAuth2Session

import paasng.utils.masked_curlify as curlify
from paasng.infras.accounts.oauth.exceptions import BKAppOauthRequestError, BKAppOauthResponseError
from paasng.utils.error_codes import error_codes

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# ignore scope warning
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


logger = logging.getLogger(__name__)


@define
class BackendDisplayInfo:
    icon: str = ""
    display_name: str = ""
    address: str = ""
    description: str = ""
    auth_docs: str = ""

    def to_dict(self):
        # A lazy version of Serializer
        return cattr.unstructure(self)


empty_display_info = BackendDisplayInfo()


@define
class OAuth2Backend:
    authorization_base_url: str
    client_id: str
    client_secret: str
    token_base_url: str
    redirect_uri: str = ""
    display_info: BackendDisplayInfo = empty_display_info
    scope: ClassVar[List[str]] = ["api"]
    # default display info, will be override by settings.
    _default_display_info: ClassVar[Dict[str, str]] = {}
    # 表示该 backend 是否支持 多 token
    supports_multi_tokens: ClassVar[bool] = False
    session: OAuth2Session = field(init=False)

    def __attrs_post_init__(self):
        self.session = self.get_oauth_session()
        # Merge default display info into the the one in settings.
        display_info_not_set = {
            f: v for f, v in self._default_display_info.items() if getattr(self.display_info, f) == "" and v
        }
        if display_info_not_set:
            self.display_info = evolve(self.display_info, **display_info_not_set)

    def __str__(self):
        return (
            f"OAuth2Backend: display_name: {self.display_info.display_name}, "
            f"address: {self.display_info.address}, desc: {self.display_info.description}"
        )

    def get_oauth_session(self) -> OAuth2Session:
        if not self.client_id:
            raise ValueError("please fulfill client id settings")
        return OAuth2Session(self.client_id)

    @staticmethod
    def get_scope(scope: List[str]) -> str:
        """获取 scope 实际内容

        :param scope: example: ["api"] or ["project:xxxx/xxx"] etc
        :return: example: "api" or "project:xxxx/xxx"
        """
        return scope[0]

    def get_auth_docs(self) -> str:
        """获取授权指引文档"""
        return self.display_info.auth_docs

    def get_authorization_url(self) -> str:
        return self.session.authorization_url(self.authorization_base_url)[0]

    def fetch_token(self, redirect_url):
        return self.session.fetch_token(
            token_url=self.token_base_url, client_secret=self.client_secret, authorization_response=redirect_url
        )

    def refresh_token(self, refresh_token: str):
        return self.session.refresh_token(
            token_url=self.token_base_url,
            client_secret=self.client_secret,
            client_id=self.client_id,
            refresh_token=refresh_token,
        )


class GitRepoBackend(OAuth2Backend):
    """Git 仓库，如 GitLab，GitHub，Gitee 等共用 Backend"""

    def get_oauth_session(self) -> OAuth2Session:
        if not self.client_id or not self.redirect_uri:
            raise ValueError("please fulfill client id & redirect_uri settings")
        return OAuth2Session(client_id=self.client_id, redirect_uri=self.redirect_uri, scope=self.scope)


class GitLabBackend(GitRepoBackend):
    _default_display_info: ClassVar[Dict[str, str]] = {"display_name": "GitLab"}


class GitHubBackend(GitRepoBackend):
    scope: ClassVar[List[str]] = ["repo"]
    _default_display_info: ClassVar[Dict[str, str]] = {"display_name": "GitHub"}


class GiteeBackend(GitRepoBackend):
    scope: ClassVar[List[str]] = ["projects"]
    _default_display_info: ClassVar[Dict[str, str]] = {"display_name": "Gitee"}


@define
class BlueKingApplicationOauthMixin:
    auth_url: str
    refresh_url: str
    validate_url: str

    app_code: str
    app_secret: str
    env_name: str

    # 不设置 type-hint, 以绕过 dataclass
    COOKIE_KEY = ""
    HEADER_KEY = ""

    @classmethod
    def from_paasv3cli(cls):
        """使用内置的 paasv3cli 应用身份"""
        return cls(
            auth_url=settings.TOKEN_AUTH_ENDPOINT,
            refresh_url=settings.TOKEN_REFRESH_ENDPOINT,
            # 借用了 bkpaas-auth 的配置项
            validate_url=settings.BKAUTH_TOKEN_CHECK_ENDPOINT,
            app_code=settings.CLI_AUTH_CODE,
            app_secret=settings.CLI_AUTH_SECRET,
            env_name=settings.AUTH_ENV_NAME,
        )

    @classmethod
    def from_workbench(cls):
        return cls(
            auth_url=settings.TOKEN_AUTH_ENDPOINT,
            refresh_url=settings.TOKEN_REFRESH_ENDPOINT,
            # 借用了 bkpaas-auth 的配置项
            validate_url=settings.BKAUTH_TOKEN_CHECK_ENDPOINT,
            app_code=settings.BKAUTH_TOKEN_APP_CODE,
            app_secret=settings.BKAUTH_TOKEN_SECRET_KEY,
            env_name=settings.AUTH_ENV_NAME,
        )

    @classmethod
    def get_user_credential_from_request(cls, request):
        try:
            return request.COOKIES[cls.COOKIE_KEY]
        except KeyError:
            pass
        try:
            return request.META[cls.HEADER_KEY]
        except KeyError:
            logger.exception("Unable to get user credentials")
            raise error_codes.CANNOT_GET_BK_USER_CREDENTIAL.f(cls.COOKIE_KEY)

    def fetch_token(self, username: str, user_credential: str) -> dict:
        raise NotImplementedError

    def refresh_token(self, refresh_token: str) -> dict:
        raise NotImplementedError

    def validate_token(self, access_token: str) -> bool:
        raise NotImplementedError

    @property
    def app_info_headers(self):
        return {
            "X-BK-APP-CODE": self.app_code,
            "X-BK-APP-SECRET": self.app_secret,
        }

    @classmethod
    def validate_response(cls, response: Response) -> dict:
        logger.debug("request bkapp oauth api: %s", curlify.to_curl(response.request))
        if not response.ok:
            raise BKAppOauthResponseError(
                error_message=response.json(), response_code=response.status_code, raw_response=response
            )

        data = response.json()
        if not data["data"]:
            raise BKAppOauthResponseError(
                error_message=f"Can't get access token from response, detail: {data}",
                response_code=response.status_code,
                raw_response=response,
            )
        return data["data"]


class APIGateWayBackend(BlueKingApplicationOauthMixin):
    COOKIE_KEY = "bk_ticket"
    HEADER_KEY = "HTTP_X_USER_BK_TICKET"

    def fetch_token(self, username: str, user_credential: str) -> dict:
        try:
            resp = requests.post(
                url=self.auth_url,
                json=dict(
                    app_code=self.app_code,
                    app_secret=self.app_secret,
                    env_name=self.env_name,
                    grant_type="authorization_code",
                    rtx=username,
                    # need_new_token=0: 如果当前 access_token 是有效的
                    # 并且过期时间大于一定时间(目前网关侧设置的是 300s), 不会重新生成，会直接返回当前有效的
                    need_new_token=0,
                    **{self.COOKIE_KEY: user_credential},
                ),
                headers=self.app_info_headers,
            )
        except Exception as e:
            raise BKAppOauthRequestError(
                error_message="request to {} failed for {}".format(self.auth_url, e), response_code=400
            )

        return self.validate_response(response=resp)

    def refresh_token(self, refresh_token: str) -> dict:
        try:
            resp = requests.post(
                url=self.refresh_url,
                params=dict(
                    app_code=self.app_code,
                    env_name=self.env_name,
                    grant_type="refresh_token",
                    refresh_token=refresh_token,
                ),
                headers=self.app_info_headers,
            )
        except Exception as e:
            raise BKAppOauthRequestError("request to {} failed for {}".format(self.refresh_url, e))

        return self.validate_response(response=resp)

    def validate_token(self, access_token: str) -> bool:
        try:
            data = requests.get(
                url=self.validate_url,
                json={"access_token": access_token},
                headers=self.app_info_headers,
            ).json()
        except Exception as e:
            raise BKAppOauthRequestError("request to {} failed for {}".format(self.refresh_url, e))

        return data.get("result")


class BKSSMBackend(BlueKingApplicationOauthMixin):
    COOKIE_KEY = "bk_token"
    HEADER_KEY = "HTTP_X_USER_BK_TOKEN"

    def fetch_token(self, username: str, user_credential: str) -> dict:
        try:
            resp = requests.post(
                url=self.auth_url,
                json=dict(
                    app_code=self.app_code,
                    app_secret=self.app_secret,
                    env_name=self.env_name,
                    grant_type="authorization_code",
                    id_provider="bk_login",
                    **{self.COOKIE_KEY: user_credential},
                ),
                headers=self.app_info_headers,
            )
        except Exception as e:
            raise BKAppOauthRequestError(
                error_message="request to {} failed for {}".format(self.auth_url, e), response_code=400
            )

        return self.validate_response(response=resp)

    def refresh_token(self, refresh_token: str) -> dict:
        try:
            resp = requests.post(
                url=self.refresh_url,
                json=dict(
                    app_code=self.app_code,
                    env_name=self.env_name,
                    grant_type="refresh_token",
                    refresh_token=refresh_token,
                ),
                headers=self.app_info_headers,
            )
        except Exception as e:
            raise BKAppOauthRequestError("request to {} failed for {}".format(self.refresh_url, e))

        return self.validate_response(response=resp)

    def validate_token(self, access_token: str) -> bool:
        try:
            data = requests.post(
                url=self.validate_url,
                json={"access_token": access_token},
                headers=self.app_info_headers,
            ).json()
        except Exception as e:
            raise BKAppOauthRequestError("request to {} failed for {}".format(self.refresh_url, e))

        return data.get("code") == 0


def get_bkapp_oauth_backend_cls():
    if settings.BKAUTH_BACKEND_TYPE == "bk_token":
        return BKSSMBackend
    else:
        return APIGateWayBackend
