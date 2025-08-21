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

import logging
from functools import partial
from math import isinf
from typing import Optional, Type, cast

import curlify
import requests

from paasng.utils.moby_distribution.registry import exceptions
from paasng.utils.moby_distribution.registry.auth import (
    AuthorizationProvider,
    BaseAuthentication,
    UniversalAuthentication,
)
from paasng.utils.moby_distribution.registry.utils import LazyProxy, TypeTimeout
from paasng.utils.moby_distribution.spec.endpoint import OFFICIAL_ENDPOINT, APIEndpoint

logger = logging.getLogger(__name__)


class DockerRegistryV2Client:
    """A Client implement APIs of Docker Registry HTTP API V2 and OCI Distribution Spec API

    spec: https://github.com/distribution/distribution/blob/main/docs/spec/api.md
    reference: https://github.com/distribution/distribution/tree/main/registry/client
    """

    @classmethod
    def from_api_endpoint(
        cls,
        api_endpoint: APIEndpoint = OFFICIAL_ENDPOINT,
        username: Optional[str] = None,
        password: Optional[str] = None,
        authenticator_class: Type[BaseAuthentication] = UniversalAuthentication,
        default_timeout: TypeTimeout = 60 * 10,
        https_detect_timeout: float = 30,
        auth_timeout: TypeTimeout = 30,
    ):
        https_scheme = "https://"
        http_scheme = "http://"
        enable_https, certificate_valid = api_endpoint.is_secure_repository(timeout=https_detect_timeout)
        if enable_https:
            client = cls(
                api_base_url=f"{https_scheme}{api_endpoint.api_base_url}",
                username=username,
                password=password,
                verify_certificate=certificate_valid,
                authenticator_class=authenticator_class,
                default_timeout=default_timeout,
                auth_timeout=auth_timeout,
            )
            if certificate_valid or client.ping():
                return client
        return cls(
            api_base_url=f"{http_scheme}{api_endpoint.api_base_url}",
            username=username,
            password=password,
            verify_certificate=False,
            authenticator_class=authenticator_class,
            default_timeout=default_timeout,
            auth_timeout=auth_timeout,
        )

    def __init__(
        self,
        api_base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_certificate: bool = True,
        authenticator_class: Type[BaseAuthentication] = UniversalAuthentication,
        default_timeout: TypeTimeout = 60 * 10,
        auth_timeout: TypeTimeout = 30,
    ):
        if default_timeout is not None and not isinstance(default_timeout, tuple) and isinf(default_timeout):
            raise ValueError("default_timeout should not be infinity.")
        if auth_timeout is not None and not isinstance(auth_timeout, tuple) and isinf(auth_timeout):
            raise ValueError("auth_timeout should not be infinity.")
        if api_base_url.endswith("/"):
            api_base_url = api_base_url.rstrip("/")
        self.api_base_url = api_base_url
        self.session = requests.session()
        self.session.verify = verify_certificate
        self.default_timeout = default_timeout
        self.auth_timeout = auth_timeout

        self.username = username
        self.password = password
        self.authenticator_class = authenticator_class
        self._authed: Optional[AuthorizationProvider] = None

    def ping(self) -> bool:
        """API Version Check."""
        url = URLBuilder.build_v2_url(self.api_base_url)
        try:
            self._request(self.session.get, url=url)
        except exceptions.RequestError:
            logger.debug("Can't not connect to server<%s>", url)
            return False
        return True

    @property
    def authorization(self) -> str:
        if self._authed is None:
            return ""
        return self._authed.provide()

    @property
    def get(self):
        return partial(self._request, self.session.get)

    @property
    def put(self):
        return partial(self._request, self.session.put)

    @property
    def patch(self):
        return partial(self._request, self.session.patch)

    @property
    def post(self):
        return partial(self._request, self.session.post)

    @property
    def delete(self):
        return partial(self._request, self.session.delete)

    @property
    def head(self):
        return partial(self._request, self.session.head)

    def _request(self, method, *, should_retry: bool = True, **kwargs):
        # here use inf as a flag to use default timeout
        kwargs.setdefault("timeout", self.default_timeout)
        if kwargs["timeout"] is not None and not isinstance(kwargs["timeout"], tuple) and isinf(kwargs["timeout"]):
            kwargs["timeout"] = self.default_timeout
        headers = kwargs.setdefault("headers", {})
        headers["Authorization"] = self.authorization
        try:
            resp = self._validate_response(method(**kwargs), auto_auth=should_retry)
        except exceptions.RetryAgain:
            return self._request(method, should_retry=False, **kwargs)
        return resp

    def _validate_response(self, resp: requests.Response, auto_auth: bool = True) -> requests.Response:
        url = resp.request.url
        try:
            curl = curlify.to_curl(resp.request)
        except Exception:
            curl = "<unknown>"

        if resp.status_code == 401:
            if auto_auth:
                www_authenticate = resp.headers["www-authenticate"]
                auth = self.authenticator_class(www_authenticate)
                self._authed = auth.authenticate(
                    username=self.username, password=self.password, timeout=self.auth_timeout
                )
                raise exceptions.RetryAgain

            logger.debug("Requesting %s, but PermissionDeny, Equivalent curl command: %s", url, curl)
            raise exceptions.PermissionDeny

        if resp.status_code == 403:
            if auto_auth and self._authed is None and self.ping():
                raise exceptions.RetryAgain

            logger.debug("Requesting %s, but PermissionDeny, Equivalent curl command: %s", url, curl)
            raise exceptions.PermissionDeny

        if resp.status_code == 404:
            logger.info("Requesting %s, but ResourceNotFound, Equivalent curl command: %s", url, curl)
            raise exceptions.ResourceNotFound

        if not resp.ok:
            logger.warning("Requesting %s, but Response Not OK, Equivalent curl command: %s", url, curl)
            raise exceptions.RequestErrorWithResponse(message=resp.text, status_code=resp.status_code, response=resp)
        return resp


class URLBuilder:
    @staticmethod
    def build_v2_url(endpoint: str) -> str:
        return f"{endpoint}/v2/"

    @staticmethod
    def build_blobs_url(endpoint: str, repo: str, digest: str) -> str:
        return f"{endpoint}/v2/{repo}/blobs/{digest}"

    @staticmethod
    def build_manifests_url(endpoint: str, repo: str, reference: str) -> str:
        return f"{endpoint}/v2/{repo}/manifests/{reference}"

    @staticmethod
    def build_upload_blobs_url(endpoint: str, repo: str) -> str:
        return f"{endpoint}/v2/{repo}/blobs/uploads/"

    @staticmethod
    def build_tags_url(endpoint: str, repo: str) -> str:
        return f"{endpoint}/v2/{repo}/tags/list"


default_client = cast(
    DockerRegistryV2Client, LazyProxy(lambda: DockerRegistryV2Client.from_api_endpoint(OFFICIAL_ENDPOINT))
)


def set_default_client(client: DockerRegistryV2Client):
    default_client.__dict__["_wrapped"] = client
