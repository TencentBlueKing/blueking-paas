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

from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.infras.sysapi_client.constants import ClientRole
from paasng.infras.sysapi_client.models import ClientPrivateToken, SysAPIClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def sys_api_client_no_perm():
    """Return an API client with BASIC_READER role (no FETCH_APP_OAUTH_TOKEN permission).

    :returns: An APIClient with insufficient permissions.
    """
    client = SysAPIClient.objects.create(name="test_reader_client", role=ClientRole.BASIC_READER)
    token = ClientPrivateToken.objects.create_token(client=client, expires_in=None)
    return APIClient(headers={"Authorization": f"Bearer {token.token}"})


@pytest.fixture()
def fetch_token_url(bk_app) -> str:
    """Return the URL for sys oauth token fetch endpoint.

    :param bk_app: The application fixture.
    :returns: The URL string.
    """
    return reverse("sys.api.applications.oauth.token", kwargs={"app_code": bk_app.code, "env_name": "prod"})


class TestSysOauthTokenViewSet:
    """Test cases for SysOauthTokenViewSet.fetch_app_token API."""

    def test_fetch_token_success(
        self,
        sys_aidev_api_client: APIClient,
        fetch_token_url: str,
        bk_app,
    ) -> None:
        """Test that AIDEV role can successfully fetch a token.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        :param fetch_token_url: The fetch token URL fixture.
        :param bk_app: The application fixture.
        """
        mock_token_data = {"access_token": "test_token", "refresh_token": "test_refresh", "expires_in": 3600}
        with (
            mock.patch("paasng.infras.accounts.views.create_app_oauth_backend") as mock_create_backend,
            mock.patch("paasng.infras.accounts.views.add_app_audit_record") as mock_audit,
        ):
            mock_backend = mock.MagicMock()
            mock_backend.fetch_token.return_value = mock_token_data
            mock_backend.get_user_credential_from_request.return_value = "fake_credential"
            mock_create_backend.return_value = mock_backend

            resp = sys_aidev_api_client.get(fetch_token_url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["access_token"] == "test_token"
        mock_audit.assert_called_once()
        audit_kwargs = mock_audit.call_args[1]
        assert audit_kwargs["app_code"] == bk_app.code
        assert "sys_client:" in audit_kwargs["attribute"]

    def test_fetch_token_denied_for_non_aidev_role(
        self,
        sys_api_client_no_perm: APIClient,
        fetch_token_url: str,
    ) -> None:
        """Test that non-AIDEV roles are denied access.

        :param sys_api_client_no_perm: The API client with BASIC_READER role.
        :param fetch_token_url: The fetch token URL fixture.
        """
        resp = sys_api_client_no_perm.get(fetch_token_url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_fetch_token_denied_for_all_non_aidev_roles(self, fetch_token_url: str) -> None:
        """Test that all non-AIDEV roles are denied access.

        :param fetch_token_url: The fetch token URL fixture.
        """
        non_aidev_roles = [
            ClientRole.NOBODY,
            ClientRole.BASIC_READER,
            ClientRole.BASIC_MAINTAINER,
            ClientRole.LIGHT_APP_MAINTAINER,
            ClientRole.LESSCODE,
        ]
        for role in non_aidev_roles:
            client = SysAPIClient.objects.create(name=f"test_{role.value}", role=role)
            token = ClientPrivateToken.objects.create_token(client=client, expires_in=None)
            api_client = APIClient(headers={"Authorization": f"Bearer {token.token}"})
            resp = api_client.get(fetch_token_url)
            assert resp.status_code == status.HTTP_403_FORBIDDEN, f"Role {role} should be denied"

    def test_fetch_token_missing_oauth_client(
        self,
        sys_aidev_api_client: APIClient,
        fetch_token_url: str,
    ) -> None:
        """Test that missing OAuth client returns the correct error.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        :param fetch_token_url: The fetch token URL fixture.
        """
        from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist

        with mock.patch(
            "paasng.infras.accounts.views.create_app_oauth_backend",
            side_effect=BkOauthClientDoesNotExist,
        ):
            resp = sys_aidev_api_client.get(fetch_token_url)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_fetch_token_oauth_error(
        self,
        sys_aidev_api_client: APIClient,
        fetch_token_url: str,
    ) -> None:
        """Test that upstream OAuth error is returned properly.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        :param fetch_token_url: The fetch token URL fixture.
        """
        from paasng.infras.accounts.oauth.exceptions import BKAppOauthError

        with mock.patch("paasng.infras.accounts.views.create_app_oauth_backend") as mock_create_backend:
            mock_backend = mock.MagicMock()
            mock_backend.fetch_token.side_effect = BKAppOauthError(
                response_code=400, error_message="upstream oauth error"
            )
            mock_backend.get_user_credential_from_request.return_value = "fake_credential"
            mock_create_backend.return_value = mock_backend

            resp = sys_aidev_api_client.get(fetch_token_url)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["message"] == "upstream oauth error"

    def test_env_name_only_test_and_prod(self, sys_aidev_api_client: APIClient, bk_app) -> None:
        """Test that only test and prod env_name are accepted, lesscode is rejected.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        :param bk_app: The application fixture.
        """
        lesscode_url = f"/sys/api/bkapps/applications/{bk_app.code}/oauth/token/lesscode/"
        resp = sys_aidev_api_client.get(lesscode_url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_app(self, sys_aidev_api_client: APIClient) -> None:
        """Test that a nonexistent app returns 404.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        """
        url = reverse(
            "sys.api.applications.oauth.token",
            kwargs={"app_code": "nonexistent-app-code", "env_name": "prod"},
        )
        resp = sys_aidev_api_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND
