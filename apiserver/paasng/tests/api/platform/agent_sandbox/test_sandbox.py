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

from typing import Any
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.exceptions import SandboxAlreadyExists, SandboxError
from paasng.platform.agent_sandbox.models import Sandbox

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAgentSandboxViewSetCreate:
    """Test cases for AgentSandboxViewSet.create API."""

    def test_create_sandbox_success(self, api_client: APIClient, bk_app: Any, sandbox_record: Sandbox) -> None:
        """Verify sandbox creation API works with mocked create_sandbox.

        :param api_client: The API client fixture.
        :param bk_app: The application fixture.
        :param sandbox_record: The sandbox record fixture (used as mock return value).
        """
        create_url = reverse("agent_sandbox.create", kwargs={"code": bk_app.code})

        with mock.patch(
            "paasng.platform.agent_sandbox.views.create_sandbox",
            return_value=sandbox_record,
        ):
            resp = api_client.post(
                create_url,
                data={
                    "name": "test-sandbox",
                    "env_vars": {"FOO": "bar"},
                    "snapshot": "python:3.11-alpine",
                    "snapshot_entrypoint": ["python", "-m", "http.server"],
                    "workspace": "/app",
                },
                format="json",
            )

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert "uuid" in data
        assert "name" in data
        assert "snapshot" in data
        assert "status" in data

    def test_create_sandbox_already_exists(self, api_client: APIClient, bk_app: Any) -> None:
        """Verify sandbox creation returns proper error when sandbox already exists.

        :param api_client: The API client fixture.
        :param bk_app: The application fixture.
        """
        create_url = reverse("agent_sandbox.create", kwargs={"code": bk_app.code})

        with mock.patch(
            "paasng.platform.agent_sandbox.views.create_sandbox",
            side_effect=SandboxAlreadyExists("sandbox already exists"),
        ):
            resp = api_client.post(create_url, data={"name": "existing-sandbox"}, format="json")

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["code"] == "AGENT_SANDBOX_ALREADY_EXISTS"

    def test_create_sandbox_failed(self, api_client: APIClient, bk_app: Any) -> None:
        """Verify sandbox creation returns proper error when creation fails.

        :param api_client: The API client fixture.
        :param bk_app: The application fixture.
        """
        create_url = reverse("agent_sandbox.create", kwargs={"code": bk_app.code})

        with mock.patch(
            "paasng.platform.agent_sandbox.views.create_sandbox",
            side_effect=SandboxError("failed to create sandbox"),
        ):
            resp = api_client.post(create_url, data={"name": "failed-sandbox"}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "AGENT_SANDBOX_CREATE_FAILED"


class TestAgentSandboxViewSetDestroy:
    """Test cases for AgentSandboxViewSet.destroy API."""

    def test_destroy_sandbox_success(self, api_client: APIClient, sandbox_record: Sandbox) -> None:
        """Verify sandbox destruction API works with mocked delete_sandbox.

        :param api_client: The API client fixture.
        :param sandbox_record: The sandbox record fixture.
        """
        destroy_url = reverse("agent_sandbox.destroy", kwargs={"sandbox_id": sandbox_record.uuid.hex})

        with mock.patch("paasng.platform.agent_sandbox.views.delete_sandbox") as mock_delete:
            resp = api_client.delete(destroy_url)

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_called_once_with(sandbox_record)

    def test_destroy_sandbox_not_found(self, api_client: APIClient) -> None:
        """Verify sandbox destruction returns 404 when sandbox not found.

        :param api_client: The API client fixture.
        """
        destroy_url = reverse("agent_sandbox.destroy", kwargs={"sandbox_id": "00000000000000000000000000000000"})
        resp = api_client.delete(destroy_url)

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_sandbox_failed(self, api_client: APIClient, sandbox_record: Sandbox) -> None:
        """Verify sandbox destruction returns proper error when deletion fails.

        :param api_client: The API client fixture.
        :param sandbox_record: The sandbox record fixture.
        """
        destroy_url = reverse("agent_sandbox.destroy", kwargs={"sandbox_id": sandbox_record.uuid.hex})

        with mock.patch(
            "paasng.platform.agent_sandbox.views.delete_sandbox",
            side_effect=SandboxError("failed to delete sandbox"),
        ):
            resp = api_client.delete(destroy_url)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "AGENT_SANDBOX_DELETE_FAILED"
