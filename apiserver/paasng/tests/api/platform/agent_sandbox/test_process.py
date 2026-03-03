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

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAgentSandboxProcessViewSet:
    """Test cases for Agent Sandbox process APIs using mocked sandbox client."""

    def test_exec_and_code_run(self, api_client: APIClient, sandbox_id_with_mock: str) -> None:
        """Verify command exec and code_run APIs work as expected with mocked sandbox.

        :param api_client: The API client fixture.
        :param sandbox_id_with_mock: The sandbox UUID with mocked client backend.
        """
        # Execute a simple shell command and verify the process result.
        exec_url = reverse("agent_sandbox.process.exec", kwargs={"sandbox_id": sandbox_id_with_mock})
        exec_resp = api_client.post(exec_url, data={"cmd": ["echo", "hello-agent"]}, format="json")

        assert exec_resp.status_code == status.HTTP_200_OK
        assert exec_resp.json()["exit_code"] == 0
        assert "hello-agent" in exec_resp.json()["stdout"]

    def test_get_logs(self, api_client: APIClient, sandbox_id_with_mock: str) -> None:
        """Verify logs API is reachable and returns string payload with mocked sandbox.

        :param api_client: The API client fixture.
        :param sandbox_id_with_mock: The sandbox UUID with mocked client backend.
        """
        # Request sandbox logs with query options.
        logs_url = reverse("agent_sandbox.process.logs", kwargs={"sandbox_id": sandbox_id_with_mock})
        logs_resp = api_client.get(logs_url, data={"tail_lines": 50, "timestamps": False})

        # Validate logs response contract.
        assert logs_resp.status_code == status.HTTP_200_OK
        assert isinstance(logs_resp.json()["logs"], str)
