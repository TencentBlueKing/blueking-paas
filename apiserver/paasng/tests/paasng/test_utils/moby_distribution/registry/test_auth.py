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
from unittest import mock

import pytest
import requests
import requests_mock

try:
    from pydantic import __version__ as pydantic_version
except ImportError:
    # pydantic <= 1.8.2 does not have __version__
    import pydantic as _pydantic

    pydantic_version = _pydantic.VERSION
from paasng.utils.moby_distribution.registry.auth import (
    DockerRegistryTokenAuthentication,
    HTTPBasicAuthentication,
    TokenAuthorizationProvider,
)
from paasng.utils.moby_distribution.registry.exceptions import AuthFailed


@pytest.fixture
def mock_adapter():
    session = requests.Session()
    adapter = requests_mock.Adapter()
    session.mount("mock://", adapter)
    with mock.patch("paasng.utils.moby_distribution.registry.auth.requests", session):
        yield adapter


@pytest.fixture
def auth_response():
    if pydantic_version.startswith("2."):
        return {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IlBZWU86VEVXVTpWN0pIOjI2SlY6QVFUWjpMSkMzOlNYVko6WEdIQTozNEYyOjJMQVE6WlJNSzpaN1E2In0.eyJpc3MiOiJhdXRoLmRvY2tlci5jb20iLCJzdWIiOiJqbGhhd24iLCJhdWQiOiJyZWdpc3RyeS5kb2NrZXIuY29tIiwiZXhwIjoxNDE1Mzg3MzE1LCJuYmYiOjE0MTUzODcwMTUsImlhdCI6MTQxNTM4NzAxNSwianRpIjoidFlKQ08xYzZjbnl5N2tBbjBjN3JLUGdiVjFIMWJGd3MiLCJhY2Nlc3MiOlt7InR5cGUiOiJyZXBvc2l0b3J5IiwibmFtZSI6InNhbWFsYmEvbXktYXBwIiwiYWN0aW9ucyI6WyJwdXNoIl19XX0.QhflHPfbd6eVF4lM9bwYpFZIV0PfikbyXuLx959ykRTBpe3CYnzs6YBK8FToVb5R47920PVLrh8zuLzdCr9t3w",
            "issued_at": "2009-11-10T23:00:00Z",
            "expires_in": 3600,
        }
    else:
        return {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IlBZWU86VEVXVTpWN0pIOjI2SlY6QVFUWjpMSkMzOlNYVko6WEdIQTozNEYyOjJMQVE6WlJNSzpaN1E2In0.eyJpc3MiOiJhdXRoLmRvY2tlci5jb20iLCJzdWIiOiJqbGhhd24iLCJhdWQiOiJyZWdpc3RyeS5kb2NrZXIuY29tIiwiZXhwIjoxNDE1Mzg3MzE1LCJuYmYiOjE0MTUzODcwMTUsImlhdCI6MTQxNTM4NzAxNSwianRpIjoidFlKQ08xYzZjbnl5N2tBbjBjN3JLUGdiVjFIMWJGd3MiLCJhY2Nlc3MiOlt7InR5cGUiOiJyZXBvc2l0b3J5IiwibmFtZSI6InNhbWFsYmEvbXktYXBwIiwiYWN0aW9ucyI6WyJwdXNoIl19XX0.QhflHPfbd6eVF4lM9bwYpFZIV0PfikbyXuLx959ykRTBpe3CYnzs6YBK8FToVb5R47920PVLrh8zuLzdCr9t3w",
            "issued_at": "2009-11-10T23:00:00+00:00",
            "expires_in": 3600,
        }


class TestDockerRegistryTokenAuthentication:
    @pytest.mark.parametrize(
        ("www_authenticate", "expected"),
        [
            (
                'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:samalba/my-app:pull,push"',
                {
                    "backend": "https://auth.docker.io/token",
                    "service": "registry.docker.io",
                    "scope": "repository:samalba/my-app:pull,push",
                },
            ),
            (
                'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:hello-world/hello-world:pull,push"',
                {
                    "backend": "https://auth.docker.io/token",
                    "service": "registry.docker.io",
                    "scope": "repository:hello-world/hello-world:pull,push",
                },
            ),
        ],
    )
    def test_properties(self, www_authenticate, expected):
        auth = DockerRegistryTokenAuthentication(www_authenticate)

        for k, v in expected.items():
            assert getattr(auth, k) == v

    def test_authenticate(self, mock_adapter, auth_response):
        www_authenticate = 'Bearer realm="mock://auth.docker.io/token",service="dummy",scope="dummy"'
        auth = DockerRegistryTokenAuthentication(www_authenticate)

        mock_adapter.register_uri("GET", "mock://auth.docker.io/token", json=auth_response)

        authed = auth.authenticate("username", "password")
        assert isinstance(authed, TokenAuthorizationProvider)
        if pydantic_version.startswith("2."):
            assert authed.token_response.model_dump(mode="json", exclude_unset=True) == auth_response  # type: ignore[attr-defined]
        else:
            assert authed.token_response.json(exclude_unset=True) == json.dumps(auth_response)

    def test_authenticate_failed(self, mock_adapter):
        www_authenticate = 'Bearer realm="mock://auth.docker.io/token",service="dummy",scope="dummy"'
        auth = DockerRegistryTokenAuthentication(www_authenticate)

        mock_adapter.register_uri("GET", "mock://auth.docker.io/token", status_code=400)
        with pytest.raises(AuthFailed):
            auth.authenticate("username", "password")


class TestHTTPBasicAuthentication:
    @pytest.mark.parametrize(
        ("username", "password", "expected"),
        [
            ("username", "password", "Basic dXNlcm5hbWU6cGFzc3dvcmQ="),
            pytest.param("username", None, "", marks=pytest.mark.xfail),
            pytest.param(None, "password", "", marks=pytest.mark.xfail),
            pytest.param(None, None, "", marks=pytest.mark.xfail),
        ],
    )
    def test_authenticate(self, username, password, expected):
        assert HTTPBasicAuthentication("").authenticate(username, password).provide() == expected
