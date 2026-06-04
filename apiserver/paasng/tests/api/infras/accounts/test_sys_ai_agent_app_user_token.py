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

from paasng.misc.audit.constants import OperationTarget
from paasng.misc.audit.models import AppOperationRecord

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class FakeOauthBackend:
    """A fake of the BK app oauth backend that returns deterministic tokens.

    Using a fake instead of MagicMock keeps the test close to the real call
    flow: the view reads the user credential from the request and passes the
    request user's username down to ``fetch_token``.
    """

    def get_user_credential_from_request(self, request) -> str:
        return "fake-bk-ticket"

    def fetch_token(self, username: str, user_credential: str) -> dict:
        return {
            "access_token": f"fake-access-token-for-{username}",
            "refresh_token": "fake-refresh-token",
            "expires_in": 3600,
        }


@pytest.fixture()
def ai_agent_app(bk_app):
    """Return an application marked as an AI Agent app.

    :param bk_app: The application fixture.
    :returns: The application with ``is_ai_agent_app=True``.
    """
    bk_app.is_ai_agent_app = True
    bk_app.save(update_fields=["is_ai_agent_app"])
    return bk_app


@pytest.fixture()
def _use_fake_oauth_backend():
    """Replace the real oauth backend with a fake one so token fetching succeeds offline."""
    with mock.patch(
        "paasng.infras.accounts.sys_views.create_app_oauth_backend",
        return_value=FakeOauthBackend(),
    ):
        yield


def _fetch_token_url(app_code: str, env_name: str = "prod") -> str:
    return reverse("sys.api.ai_agent_apps.user_token", kwargs={"app_code": app_code, "env_name": env_name})


class TestSysAIAgentAppUserTokenViewSet:
    """Test cases for SysAIAgentAppUserTokenViewSet.fetch_user_token API."""

    @pytest.mark.usefixtures("_use_fake_oauth_backend")
    def test_fetch_user_token_success(self, sys_aidev_api_client: APIClient, ai_agent_app) -> None:
        """With a fake oauth backend, the AIDEV client can fetch a user token and an audit record is written.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        :param ai_agent_app: The AI Agent application fixture.
        """
        resp = sys_aidev_api_client.get(_fetch_token_url(ai_agent_app.code))

        assert resp.status_code == status.HTTP_200_OK
        # The fake backend's token payload is propagated as-is, proving the full view flow ran.
        assert resp.data["access_token"].startswith("fake-access-token-for-")
        assert resp.data["refresh_token"] == "fake-refresh-token"

        # The successful issuance should leave an ACCESS_TOKEN audit record behind.
        assert AppOperationRecord.objects.filter(
            app_code=ai_agent_app.code, target=OperationTarget.ACCESS_TOKEN
        ).exists()

    @pytest.mark.usefixtures("_use_fake_oauth_backend")
    def test_rejected_for_non_ai_agent_app(self, sys_aidev_api_client: APIClient, bk_app) -> None:
        """A non-AI-Agent app is rejected before any token is issued.

        :param sys_aidev_api_client: The authenticated AIDEV API client fixture.
        :param bk_app: A regular (non-AI-Agent) application fixture.
        """
        resp = sys_aidev_api_client.get(_fetch_token_url(bk_app.code))

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # No token is issued, so no ACCESS_TOKEN audit record should be created.
        assert not AppOperationRecord.objects.filter(
            app_code=bk_app.code, target=OperationTarget.ACCESS_TOKEN
        ).exists()

    def test_denied_without_permission(self, sys_api_client: APIClient, ai_agent_app) -> None:
        """A client without the AIDEV role is denied (sanity check on the permission guard).

        :param sys_api_client: An API client with BASIC_MAINTAINER role (no AIDEV permission).
        :param ai_agent_app: The AI Agent application fixture.
        """
        resp = sys_api_client.get(_fetch_token_url(ai_agent_app.code))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
