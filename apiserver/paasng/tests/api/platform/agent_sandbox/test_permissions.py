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

from paasng.accessories.cloudapi_v2.apigateway.exceptions import ApiGatewayServiceError
from paasng.infras.sysapi_client.constants import ClientRole
from paasng.infras.sysapi_client.models import ClientPrivateToken, SysAPIClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

client_with_no_perm = APIClient()


@pytest.fixture()
def bk_ai_agent_app(bk_app):
    """Return an application with is_ai_agent_app=True.

    :param bk_app: The base application fixture.
    :returns: The application with AI agent flag enabled.
    """
    bk_app.is_ai_agent_app = True
    bk_app.save(update_fields=["is_ai_agent_app"])
    return bk_app


@pytest.fixture()
def sys_api_client_without_perm(bk_user):
    """Return an API client without grant permission."""
    client = SysAPIClient.objects.create(name="test_aidev_client", role=ClientRole.BASIC_READER)
    token = ClientPrivateToken.objects.create_token(client=client, expires_in=None)
    # Use the private token to authenticate the client
    return APIClient(headers={"Authorization": f"Bearer {token.token}"})


class TestAgentSandboxPermissionViewSetGrantPermissions:
    """Test cases for AgentSandboxPermissionViewSet.grant_permissions API."""

    @pytest.fixture()
    def grant_url(self) -> str:
        """Return the URL for grant permissions endpoint.

        :returns: The URL string.
        """
        return reverse("agent_sandbox.permissions.grant")

    def test_grant_permissions_success(
        self,
        sys_aidev_api_client: APIClient,
        grant_url: str,
        bk_ai_agent_app,
    ) -> None:
        """Test grant permissions returns 201 on success.

        :param sys_aidev_api_client: The authenticated API client fixture.
        :param grant_url: The grant URL fixture.
        :param bk_ai_agent_app: The AI agent application fixture.
        """
        with mock.patch("paasng.platform.agent_sandbox.views.ApiGatewayClient") as mock_client_class:
            mock_client = mock.MagicMock()
            mock_client.grant_apigw_permissions.return_value = ""
            mock_client_class.return_value = mock_client

            resp = sys_aidev_api_client.post(
                grant_url,
                data={"target_app_code": bk_ai_agent_app.code, "expire_days": 180},
                format="json",
            )

        assert resp.status_code == status.HTTP_201_CREATED
        mock_client.grant_apigw_permissions.assert_called_once()
        call_kwargs = mock_client.grant_apigw_permissions.call_args[1]
        assert call_kwargs["expire_days"] == 180

    def test_grant_permissions_app_not_found(
        self,
        sys_aidev_api_client: APIClient,
        grant_url: str,
    ) -> None:
        """Test grant permissions returns 400 when target app not found.

        :param sys_aidev_api_client: The authenticated API client fixture.
        :param grant_url: The grant URL fixture.
        """
        resp = sys_aidev_api_client.post(
            grant_url,
            data={"target_app_code": "non-existent-app", "expire_days": 0},
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_grant_permissions_denied(
        self,
        sys_api_client_without_perm: APIClient,
        grant_url: str,
        bk_ai_agent_app,
    ) -> None:
        """Test grant permissions returns 403 when client lacks permission.

        :param sys_api_client_without_perm: The authenticated API client without grant permission.
        :param grant_url: The grant URL fixture.
        :param bk_ai_agent_app: The AI agent application fixture.
        """
        resp = sys_api_client_without_perm.post(
            grant_url,
            data={"target_app_code": bk_ai_agent_app.code},
            format="json",
        )

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_grant_permissions_downstream_error(
        self,
        sys_aidev_api_client: APIClient,
        grant_url: str,
        bk_ai_agent_app,
    ) -> None:
        """Test grant permissions returns error when downstream API fails.

        Note: The REMOTE_REQUEST_ERROR error code returns 400 by default.

        :param sys_aidev_api_client: The authenticated API client fixture.
        :param grant_url: The grant URL fixture.
        :param bk_ai_agent_app: The AI agent application fixture.
        """
        with mock.patch("paasng.platform.agent_sandbox.views.ApiGatewayClient") as mock_client_class:
            mock_client = mock.MagicMock()
            mock_client.grant_apigw_permissions.side_effect = ApiGatewayServiceError(
                "grant apigw permissions error: API error"
            )
            mock_client_class.return_value = mock_client

            resp = sys_aidev_api_client.post(
                grant_url,
                data={"target_app_code": bk_ai_agent_app.code},
                format="json",
            )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
