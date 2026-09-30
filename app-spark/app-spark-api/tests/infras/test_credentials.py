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

"""Which login cookie is read off a request, following BKAUTH_BACKEND_TYPE."""

import pytest
from django.test import RequestFactory

from app_spark_api.infras.accounts.credentials import get_user_credential
from app_spark_api.infras.bk_access_token import UserCredential, UserCredentialType
from tests.helpers import create_user


def make_request(bk_user, *, cookies: dict[str, str] | None = None, headers: dict[str, str] | None = None):
    """Build a request that login_required has already authenticated as ``bk_user``."""
    request = RequestFactory().get("/", headers=headers or {})
    request.COOKIES.update(cookies or {})
    request.auth = bk_user
    return request


@pytest.fixture()
def alice():
    """An authenticated user named alice."""
    return create_user(username="alice")


@pytest.mark.parametrize(
    ("backend_type", "credential_type", "value"),
    [
        ("bk_token", UserCredentialType.BK_TOKEN, "token-cookie"),
        ("bk_ticket", UserCredentialType.BK_TICKET, "ticket-cookie"),
    ],
)
def test_the_cookie_matching_the_backend_type_is_read(settings, alice, backend_type, credential_type, value):
    settings.BKAUTH_BACKEND_TYPE = backend_type
    request = make_request(alice, cookies={"bk_token": "token-cookie", "bk_ticket": "ticket-cookie"})

    assert get_user_credential(request) == UserCredential(type=credential_type, value=value, username="alice")


def test_a_proxy_header_stands_in_for_a_stripped_cookie(settings, alice):
    settings.BKAUTH_BACKEND_TYPE = "bk_token"

    credential = get_user_credential(make_request(alice, headers={"X-User-Bk-Token": "from-header"}))

    assert credential is not None
    assert credential.value == "from-header"


def test_a_request_without_the_login_has_no_credential(settings, alice):
    settings.BKAUTH_BACKEND_TYPE = "bk_token"

    # The other backend's cookie does not count: the token service would not accept it.
    assert get_user_credential(make_request(alice, cookies={"bk_ticket": "ticket-cookie"})) is None
