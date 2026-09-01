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

"""The API-wide exception handler, independent of any particular endpoint."""

from __future__ import annotations

import json
from http import HTTPStatus

import pytest
from django.test import RequestFactory

from app_spark_api.agent.runtime import (
    AgentBusyError,
    AgentProvisionError,
    AgentUnavailableError,
    AgentWorkspaceBusyError,
)
from app_spark_api.api import handle_agent_runtime_error

SECRET = "internal-secret-token"


@pytest.mark.parametrize(
    ("exc", "status", "detail"),
    [
        (
            AgentBusyError(f"a run is already in progress: {SECRET}"),
            HTTPStatus.CONFLICT,
            "The Agent Runtime is already executing a run for this conversation.",
        ),
        (
            AgentWorkspaceBusyError(f"Conversation conv-{SECRET} already has a running Agent."),
            HTTPStatus.CONFLICT,
            "Another conversation already has a running Agent on this project.",
        ),
        (
            AgentUnavailableError(f"Could not reach the Agent Runtime: {SECRET}"),
            HTTPStatus.BAD_GATEWAY,
            "The Agent Runtime is unavailable.",
        ),
        (
            AgentProvisionError(f"The Agent Runtime exited during startup:\n{SECRET}"),
            HTTPStatus.BAD_GATEWAY,
            "The Agent Runtime is unavailable.",
        ),
    ],
)
def test_agent_runtime_errors_do_not_leak_internal_details(exc, status, detail):
    response = handle_agent_runtime_error(RequestFactory().get("/"), exc)

    body = json.loads(response.content)
    assert response.status_code == status
    assert body == {"detail": detail}
    assert SECRET not in response.content.decode()
