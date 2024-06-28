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

from typing import NamedTuple

import pytest
from rest_framework import viewsets
from rest_framework.test import APIRequestFactory

from paasng.infras.accounts.middlewares import AuthenticatedAppAsUserMiddleware, PrivateTokenAuthenticationMiddleware
from paasng.infras.accounts.models import AuthenticatedAppAsUser, User, UserPrivateToken
from paasng.infras.accounts.utils import ForceAllowAuthedApp

pytestmark = pytest.mark.django_db

request_factory = APIRequestFactory(enforce_csrf_checks=False)


def get_response(request):
    return None


class TestPrivateTokenAuthenticationMiddleware:
    def test_no_token_provided(self):
        request = request_factory.get("/")

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert not hasattr(request, "user")

    def test_random_invalid_token(self):
        request = request_factory.get("/")

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert not hasattr(request, "user")

    def test_valid_token_provided(self):
        user = User.objects.create(username="foo_user")
        token = UserPrivateToken.objects.create_token(user=user, expires_in=None)

        # Provide token in query string
        request = request_factory.get("/", {"private_token": token.token})

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert request.user.username == "foo_user"
        assert request.user.is_authenticated

    def test_valid_token_provided_by_header(self):
        user = User.objects.create(username="foo_user")
        token = UserPrivateToken.objects.create_token(user=user, expires_in=None)

        # Provide token in query string
        request = request_factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token.token}")

        middleware = PrivateTokenAuthenticationMiddleware(get_response)
        middleware(request)
        assert request.user.username == "foo_user"
        assert request.user.is_authenticated


class SimpleApp(NamedTuple):
    """Simulating App type in `apigw_manager` module"""

    bk_app_code: str
    verified: bool


@ForceAllowAuthedApp.mark_view_set
class ForTestMarkedAuthViewSet(viewsets.ViewSet):
    pass


class ForTestNotMarkedAuthViewSet(viewsets.ViewSet):
    pass


class TestAuthenticatedAppAsUserMiddleware:
    @pytest.mark.parametrize(
        ("app", "marked_as_force_allow", "expected_username"),
        [
            (SimpleApp(bk_app_code="foo", verified=True), False, "foo-user"),
            (SimpleApp(bk_app_code="foo", verified=False), False, ""),
            (SimpleApp(bk_app_code="bar", verified=True), False, ""),
            # When view set has been marked as "force allow authed app", an user will be created
            (SimpleApp(bk_app_code="bar", verified=True), True, "authed-app-bar"),
            (SimpleApp(bk_app_code="bar", verified=False), True, ""),
            (None, False, ""),
        ],
    )
    def test_verified_app_provided(self, app, marked_as_force_allow, expected_username):
        # Set up data fixtures
        user = User.objects.create(username="foo-user")
        AuthenticatedAppAsUser.objects.create(user=user, bk_app_code="foo")

        request = request_factory.get("/")
        if app:
            request.app = app

        view_func = (
            ForTestMarkedAuthViewSet.as_view({"get": "retrieve"})
            if marked_as_force_allow
            else ForTestNotMarkedAuthViewSet.as_view({"get": "retrieve"})
        )
        AuthenticatedAppAsUserMiddleware(get_response).process_view(request, view_func, None, None)
        if expected_username:
            assert request.user.username == expected_username
            assert request.user.is_authenticated
        else:
            assert not hasattr(request, "user")
