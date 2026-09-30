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
    AgentWorkspaceSavePendingError,
    ModelAccessConfigurationError,
    ModelCredentialMissingError,
)
from app_spark_api.api import api
from app_spark_api.error_codes import error_codes
from app_spark_api.infras.bk_access_token import AccessTokenUnavailableError

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
            AgentWorkspaceSavePendingError(SECRET),
            HTTPStatus.CONFLICT,
            "The previous turn's files have not been saved to this project's repository yet.",
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
    response = api.on_exception(RequestFactory().get("/"), exc)

    body = json.loads(response.content)
    assert response.status_code == status
    assert body["detail"] == detail
    assert (
        body["code"]
        == {
            AgentBusyError: "AGENT_BUSY",
            AgentWorkspaceBusyError: "AGENT_WORKSPACE_BUSY",
            AgentWorkspaceSavePendingError: "AGENT_WORKSPACE_SAVE_PENDING",
            AgentUnavailableError: "AGENT_UNAVAILABLE",
            AgentProvisionError: "AGENT_UNAVAILABLE",
        }[type(exc)]
    )
    assert SECRET not in response.content.decode()


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        # An operator's problem, even though ModelAccessConfigurationError is also an
        # AgentRuntimeError: the nearest base class has to win, or it would read as a dead Runtime.
        (
            ModelAccessConfigurationError(f"Invalid BkAidevModelConfig: {SECRET}"),
            503,
            "MODEL_ACCESS_CONFIGURATION_ERROR",
        ),
        (ModelCredentialMissingError(SECRET), 401, "MODEL_CREDENTIAL_MISSING"),
        (AccessTokenUnavailableError(f"refused: {SECRET}"), 502, "MODEL_ACCESS_TOKEN_UNAVAILABLE"),
    ],
)
def test_model_access_errors_say_who_has_to_fix_them(exc, status, code):
    response = api.on_exception(RequestFactory().get("/"), exc)

    assert response.status_code == status
    assert json.loads(response.content)["code"] == code
    assert SECRET not in response.content.decode()


@pytest.mark.parametrize("name", ["PROJECT_ID_TAKEN", "PROJECT_NAME_TAKEN"])
def test_error_code_instances_do_not_share_message_or_data(name):
    first = getattr(error_codes, name).f(project_id="one", name="one").set_data({"one": True})
    second = getattr(error_codes, name).f(project_id="two", name="two")
    assert first.code == second.code == name
    assert "one" in first.message
    assert "two" in second.message
    assert second.data is None


def test_unexpected_errors_are_masked_even_in_debug_mode(settings, caplog):
    settings.DEBUG = True
    response = api.on_exception(RequestFactory().get("/"), RuntimeError(SECRET))
    assert response.status_code == 500
    assert json.loads(response.content) == {
        "code": "INTERNAL_SERVER_ERROR",
        "detail": "An internal server error occurred.",
    }
    assert SECRET not in response.content.decode()
    assert SECRET in caplog.text


def test_api_error_uses_its_code_message_and_http_status():
    error = error_codes.PROJECT_ID_TAKEN.f(project_id="example")
    response = api.on_exception(RequestFactory().get("/"), error)
    assert response.status_code == 409
    assert json.loads(response.content) == {
        "code": "PROJECT_ID_TAKEN",
        "detail": "Project id `example` is already taken.",
    }


@pytest.mark.django_db(transaction=True)
def test_handled_error_rolls_back_an_atomic_request(project):
    from django.db import connection, transaction

    from app_spark_api.core.projects.models import Project

    old = connection.settings_dict["ATOMIC_REQUESTS"]
    connection.settings_dict["ATOMIC_REQUESTS"] = True
    try:
        with transaction.atomic():
            Project.objects.filter(pk=project.pk).update(name="must roll back")
            api.on_exception(RequestFactory().get("/"), error_codes.BAD_REQUEST)
        project.refresh_from_db()
        assert project.name != "must roll back"
    finally:
        connection.settings_dict["ATOMIC_REQUESTS"] = old


def test_openapi_declares_the_same_error_shape_for_internal_and_public_routes():
    schema = json.loads(json.dumps(api.get_openapi_schema()))
    assert {"code", "detail"} <= set(schema["components"]["schemas"]["ErrorResponse"]["required"])
    for path in ("/api/projects/", "/api/internal/conversations/{conversation_id}/state/messages"):
        for status in ("401", "422", "500"):
            error_schema = schema["paths"][path]["post"]["responses"][status]["content"]["application/json"]["schema"]
            assert error_schema == {"$ref": "#/components/schemas/ErrorResponse"}


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "BAD_REQUEST"),
        (401, "AUTHENTICATION_REQUIRED"),
        (403, "PERMISSION_DENIED"),
        (404, "RESOURCE_NOT_FOUND"),
        (405, "METHOD_NOT_ALLOWED"),
        (422, "VALIDATION_ERROR"),
        (429, "THROTTLED"),
    ],
)
def test_framework_http_errors_have_codes_and_do_not_echo_raw_messages(status, code):
    from ninja.errors import HttpError

    response = api.on_exception(RequestFactory().get("/"), HttpError(status, SECRET))
    assert response.status_code == status
    assert json.loads(response.content)["code"] == code
    assert SECRET not in response.content.decode()


def test_archived_state_and_storage_configuration_errors_have_distinct_codes():
    from app_spark_api.agent.conversations.state import ConversationStateError
    from app_spark_api.repository.storage.exceptions import StorageConfigurationError

    for exc, code, status in (
        (ConversationStateError(SECRET), "CONVERSATION_STATE_UNAVAILABLE", 500),
        (StorageConfigurationError(SECRET), "STORAGE_CONFIGURATION_ERROR", 503),
    ):
        response = api.on_exception(RequestFactory().get("/"), exc)
        assert response.status_code == status
        assert json.loads(response.content)["code"] == code
        assert SECRET not in response.content.decode()
