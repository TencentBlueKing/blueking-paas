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

from unittest import mock

import pytest
from django.contrib.auth import user_logged_in
from django.contrib.auth.backends import BaseBackend
from django.test import AsyncClient, Client


class FakeMiddleware:
    """A no-op replacement for authentication middleware in tests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class FakeBackend(BaseBackend):
    """Keep force-logged-in users available without calling a real auth service."""

    _users: dict[str, object] = {}

    @classmethod
    def remember_logged_in_user(cls, **kwargs):
        user = kwargs["user"]
        cls._users[str(user.pk)] = user

    def get_user(self, user_id):
        return self._users.get(str(user_id))

    async def aget_user(self, user_id):
        return self.get_user(user_id)


@pytest.fixture(autouse=True)
def _mock_bkpaas_auth(settings):
    """Replace external authentication with an in-memory backend."""
    # Replace backend so the user can be loaded.
    backend_path = f"{FakeBackend.__module__}.{FakeBackend.__qualname__}"
    settings.AUTHENTICATION_BACKENDS = [backend_path]

    # Keep sessions visible to both sync fixture setup and async test requests.
    #
    # By default, the project uses MySQL for session storage, and there is an isolation issue
    # between the api_client and the testcase. The login action that modified the session
    # was isolated from the testcase because they are in two different transactions.
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

    FakeBackend._users.clear()
    user_logged_in.connect(
        FakeBackend.remember_logged_in_user,
        dispatch_uid="tests.api.conftest.remember_logged_in_user",
        weak=False,
    )

    try:
        with mock.patch("bkpaas_auth.middlewares.CookieLoginMiddleware", new=FakeMiddleware):
            yield
    finally:
        user_logged_in.disconnect(dispatch_uid="tests.api.conftest.remember_logged_in_user")
        FakeBackend._users.clear()


@pytest.fixture()
def api_client(bk_user) -> Client:
    """Return Django's sync client with an logged in user."""
    client = Client()
    client.force_login(bk_user)
    return client


@pytest.fixture()
def aapi_client(bk_user) -> AsyncClient:
    """Return Django's async client with an logged in user."""
    aclient = AsyncClient()
    aclient.force_login(bk_user)
    return aclient


@pytest.fixture()
def aanonymous_api_client() -> AsyncClient:
    """Return Django's async client with an anonymous user."""
    return AsyncClient()
