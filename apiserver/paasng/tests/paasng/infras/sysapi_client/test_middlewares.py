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
from dataclasses import dataclass

import pytest
from rest_framework import viewsets
from rest_framework.test import APIRequestFactory

from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.infras.sysapi_client.constants import ClientRole
from paasng.infras.sysapi_client.middlewares import (
    AuthenticatedAppAsClientMiddleware,
    PrivateTokenAuthenticationMiddleware,
)
from paasng.infras.sysapi_client.models import AuthenticatedAppAsClient, ClientPrivateToken, SysAPIClient

pytestmark = pytest.mark.django_db

request_factory = APIRequestFactory(enforce_csrf_checks=False)


def get_response(request):
    return None


class TestPrivateTokenAuthenticationMiddleware:
    def test_no_token_provided(self):
        request = request_factory.get("/")

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert not hasattr(request, "sysapi_client")

    def test_random_invalid_token(self):
        request = request_factory.get("/")

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert not hasattr(request, "sysapi_client")

    @pytest.mark.parametrize(
        "request_maker",
        [
            # Token in query string
            lambda token: request_factory.get("/", {"private_token": token}),
            # Token in Authorization header
            lambda token: request_factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}"),
        ],
        ids=["query_param", "auth_header"],
    )
    def test_valid_token_authentication(self, request_maker):
        client = SysAPIClient.objects.create(name="foo_client", role=ClientRole.BASIC_READER)
        token = ClientPrivateToken.objects.create_token(client=client, expires_in=None)

        # Create request using the parameterized request maker
        request = request_maker(token.token)

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert request.sysapi_client.name == "foo_client"


@dataclass
class SimpleApp:
    """Simulating App type in `apigw_manager` module"""

    bk_app_code: str
    verified: bool


@ForceAllowAuthedApp.mark_view_set
class ForTestMarkedAuthViewSet(viewsets.ViewSet):
    pass


class ForTestNotMarkedAuthViewSet(viewsets.ViewSet):
    pass


class TestAuthenticatedAppAsClientMiddleware:
    @pytest.mark.parametrize(
        ("app", "marked_as_force_allow", "expected_name"),
        [
            (SimpleApp(bk_app_code="foo", verified=True), False, "foo-client"),
            (SimpleApp(bk_app_code="foo", verified=False), False, ""),
            (SimpleApp(bk_app_code="bar", verified=True), False, ""),
            # When view set has been marked as "force allow authed app", a new client will be created
            (SimpleApp(bk_app_code="bar", verified=True), True, "authed-app-bar"),
            (SimpleApp(bk_app_code="bar", verified=False), True, ""),
            (None, False, ""),
        ],
    )
    def test_verified_app_provided(self, app, marked_as_force_allow, expected_name):
        # Set up data fixtures
        client = SysAPIClient.objects.create(name="foo-client", role=ClientRole.BASIC_READER)
        AuthenticatedAppAsClient.objects.create(client=client, bk_app_code="foo")

        request = request_factory.get("/")
        if app:
            request.app = app

        view_func = (
            ForTestMarkedAuthViewSet.as_view({"get": "retrieve"})
            if marked_as_force_allow
            else ForTestNotMarkedAuthViewSet.as_view({"get": "retrieve"})
        )
        AuthenticatedAppAsClientMiddleware(get_response).process_view(request, view_func, None, None)
        if expected_name:
            assert request.sysapi_client.name == expected_name
            assert request.sysapi_client.is_active is True
        else:
            assert not hasattr(request, "sysapi_client")

    @pytest.mark.parametrize(
        ("is_active", "should_have_client"),
        [
            (True, True),
            (False, False),
        ],
    )
    def test_client_activeness(self, is_active, should_have_client):
        client = SysAPIClient.objects.create(name="foo-client", role=ClientRole.BASIC_READER, is_active=is_active)
        AuthenticatedAppAsClient.objects.create(client=client, bk_app_code="foo")

        request = request_factory.get("/")
        request.app = SimpleApp(bk_app_code="foo", verified=True)

        view_func = ForTestNotMarkedAuthViewSet.as_view({"get": "retrieve"})
        AuthenticatedAppAsClientMiddleware(get_response).process_view(request, view_func, None, None)

        if should_have_client:
            assert request.sysapi_client.name == "foo-client"
            assert request.sysapi_client.is_active is True
        else:
            assert not hasattr(request, "sysapi_client")
