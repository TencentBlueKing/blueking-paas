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

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from blue_krill.web.std_error import APIError
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.http import Http404
from ninja import NinjaAPI, Router
from ninja.errors import AuthenticationError, HttpError, ValidationError

from app_spark_api.agent.conversations.api import router as conversations_router
from app_spark_api.agent.conversations.exceptions import ConversationClosedError, InvalidHistoryCursorError
from app_spark_api.agent.conversations.internal_api import router as conversation_state_router
from app_spark_api.agent.conversations.state import ConversationStateError
from app_spark_api.agent.runtime import (
    AgentBusyError,
    AgentRuntimeError,
    AgentWorkspaceBusyError,
    AgentWorkspaceSavePendingError,
)
from app_spark_api.core.projects.api import router as projects_router
from app_spark_api.error_codes import error_codes
from app_spark_api.infras.accounts.api import router as accounts_router
from app_spark_api.infras.forgejo.exceptions import ForgejoError
from app_spark_api.repository.git.api import router as git_repository_router
from app_spark_api.repository.git.exceptions import GitRepositoryNotReadyError, RepoServerConfigurationError
from app_spark_api.repository.storage.exceptions import StorageConfigurationError

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

root_router = Router()
root_router.add_router("/accounts/", accounts_router)
root_router.add_router("/projects/", projects_router)
root_router.add_router("/projects/{project_id}/git-repository/", git_repository_router)
root_router.add_router("/projects/{project_id}/conversations/", conversations_router)
# Mounted under `/internal/` and addressed by conversation id rather than by project and
# number: the caller is an Agent Runtime this service started, it has no user and no project
# context, and the token it holds names exactly one conversation. Keeping it off the
# project-scoped prefix is also what keeps it visibly out of the user-facing surface.
root_router.add_router("/internal/conversations/", conversation_state_router)

api = NinjaAPI(title="App Spark API", urls_namespace="api")
api.add_router("", root_router)


# Translate integration failures at the API boundary. The original message is
# for operators, not callers: it may name a sibling conversation, quote the
# Agent's own body, or include a process log tail.
_EXCEPTION_ERROR_CODES: dict[type[Exception], APIError] = {
    RepoServerConfigurationError: error_codes.REPO_SERVER_CONFIGURATION_ERROR,
    ForgejoError: error_codes.REPO_SERVER_UNAVAILABLE,
    GitRepositoryNotReadyError: error_codes.GIT_REPOSITORY_NOT_READY,
    # Both closing and advancing a conversation can fail this way; retrying
    # cannot reopen a closed conversation.
    ConversationClosedError: error_codes.CONVERSATION_CLOSED,
    InvalidHistoryCursorError: error_codes.INVALID_HISTORY_CURSOR,
    ConversationStateError: error_codes.CONVERSATION_STATE_UNAVAILABLE,
    StorageConfigurationError: error_codes.STORAGE_CONFIGURATION_ERROR,
    AgentBusyError: error_codes.AGENT_BUSY,
    AgentWorkspaceBusyError: error_codes.AGENT_WORKSPACE_BUSY,
    AgentWorkspaceSavePendingError: error_codes.AGENT_WORKSPACE_SAVE_PENDING,
    AgentRuntimeError: error_codes.AGENT_UNAVAILABLE,
    AuthenticationError: error_codes.AUTHENTICATION_REQUIRED,
    PermissionDenied: error_codes.PERMISSION_DENIED,
    Http404: error_codes.RESOURCE_NOT_FOUND,
    ValidationError: error_codes.VALIDATION_ERROR,
    Exception: error_codes.INTERNAL_SERVER_ERROR,
}
_HTTP_ERROR_CODES: dict[int, APIError] = {
    error.status_code: error
    for error in (
        error_codes.BAD_REQUEST,
        error_codes.AUTHENTICATION_REQUIRED,
        error_codes.PERMISSION_DENIED,
        error_codes.RESOURCE_NOT_FOUND,
        error_codes.METHOD_NOT_ALLOWED,
        error_codes.VALIDATION_ERROR,
        error_codes.THROTTLED,
    )
}


@api.exception_handler(APIError)
def handle_api_error(request: HttpRequest, exc: APIError) -> HttpResponse:
    """Serialize a public error and preserve request-transaction rollback.

    Like DRF's set_rollback, only mark an active ATOMIC_REQUESTS transaction.
    Async operations keep their explicit transactions in synchronous services;
    those unwind before reaching this handler.
    """
    for connection in connections.all(initialized_only=True):
        if connection.settings_dict["ATOMIC_REQUESTS"] and connection.in_atomic_block:
            connection.set_rollback(True)
    data = {"code": exc.code, "detail": str(exc.message)}
    if exc.data is not None:
        data["data"] = exc.data
    return api.create_response(request, data, status=exc.status_code)


def handle_exception(request: HttpRequest, exc: Exception) -> HttpResponse:
    """Translate a domain/framework exception, then use the APIError handler.

    This only covers failures before a response begins. Once an event stream
    is underway, its status is already sent and errors remain AG-UI RUN_ERROR
    events instead.
    """
    if isinstance(exc, HttpError):
        error = _HTTP_ERROR_CODES.get(exc.status_code, error_codes.INTERNAL_SERVER_ERROR)
    else:
        # Match the nearest base class, not dictionary insertion order: a busy
        # Runtime must stay a conflict even though it is also an integration error.
        error = next(_EXCEPTION_ERROR_CODES[base] for base in type(exc).__mro__ if base in _EXCEPTION_ERROR_CODES)
    if error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        logger.error("API request failed (%s)", error.code, exc_info=exc)
    return handle_api_error(request, error.format())


for exception_type in (*_EXCEPTION_ERROR_CODES, HttpError):
    api.exception_handler(exception_type)(handle_exception)
