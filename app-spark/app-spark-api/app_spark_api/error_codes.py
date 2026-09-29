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

"""Public API error codes. Names are stable identifiers for callers.

Raise ``error_codes.PROJECT_ID_TAKEN.f(project_id="demo")`` at an API boundary;
keep infrastructure exception messages out of public responses.
"""

from http import HTTPStatus

from blue_krill.web.std_error import ErrorCode
from django.utils.translation import gettext_lazy as _


class ErrorCodes:
    """The service's error vocabulary, backed by blue-krill descriptors."""

    # --- Framework-level failures -----------------------------------------------------------------
    # Raised by django-ninja or Django itself, not by this codebase, and matched in `api.py` by
    # status code rather than by name. Seeing one of these means the request was turned away
    # before any domain operation got to run, so none of them names a resource.
    BAD_REQUEST = ErrorCode(_("Invalid request."), status_code=HTTPStatus.BAD_REQUEST)
    AUTHENTICATION_REQUIRED = ErrorCode(_("Authentication is required."), status_code=HTTPStatus.UNAUTHORIZED)
    PERMISSION_DENIED = ErrorCode(_("Permission denied."), status_code=HTTPStatus.FORBIDDEN)
    RESOURCE_NOT_FOUND = ErrorCode(_("Resource not found."), status_code=HTTPStatus.NOT_FOUND)
    METHOD_NOT_ALLOWED = ErrorCode(_("Method not allowed."), status_code=HTTPStatus.METHOD_NOT_ALLOWED)
    VALIDATION_ERROR = ErrorCode(_("Request validation failed."), status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    THROTTLED = ErrorCode(_("Too many requests."), status_code=HTTPStatus.TOO_MANY_REQUESTS)
    INTERNAL_SERVER_ERROR = ErrorCode(
        _("An internal server error occurred."), status_code=HTTPStatus.INTERNAL_SERVER_ERROR
    )

    # --- Projects ---------------------------------------------------------------------------------
    PROJECT_ID_TAKEN = ErrorCode(_("Project id `{project_id}` is already taken."), status_code=HTTPStatus.CONFLICT)
    PROJECT_NAME_TAKEN = ErrorCode(_("Project name `{name}` is already taken."), status_code=HTTPStatus.CONFLICT)
    # A missing Project has no code of its own: `aget_object_or_404` already says it plainly, and
    # the endpoints nested under one only need the *inner* resource to be named. See RESOURCE_NOT_FOUND.

    # --- Conversations ----------------------------------------------------------------------------
    CONVERSATION_NOT_FOUND = ErrorCode(_("No such conversation."), status_code=HTTPStatus.NOT_FOUND)
    CONVERSATION_CLOSED = ErrorCode(_("This conversation has been closed."), status_code=HTTPStatus.CONFLICT)
    # The history cursor is opaque and only this service issues them, so a cursor it does not
    # recognize is the caller having made one up -- not a conversation that moved on.
    INVALID_HISTORY_CURSOR = ErrorCode(_("The history cursor is invalid."), status_code=HTTPStatus.BAD_REQUEST)

    # --- Conversation state write-back ------------------------------------------------------------
    # The Agent Runtime's replication path. The split that matters: `INVALID_` is the Runtime
    # pushing something this service refuses to store, which it can fix by re-sending; the other
    # two are this side being unable to hold or read the archive, which it cannot.
    INVALID_CONVERSATION_STATE = ErrorCode(
        _("The conversation state is invalid."), status_code=HTTPStatus.UNPROCESSABLE_ENTITY
    )
    CONVERSATION_STATE_UNAVAILABLE = ErrorCode(
        _("The saved conversation state is unavailable."),
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    STORAGE_CONFIGURATION_ERROR = ErrorCode(
        _("Storage is not configured correctly. Please contact an administrator."),
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
    )
    INVALID_JSON_BODY = ErrorCode(_("Invalid JSON body."), status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    JSON_OBJECT_REQUIRED = ErrorCode(_("Expected a JSON object."), status_code=HTTPStatus.UNPROCESSABLE_ENTITY)

    # --- Git repository ---------------------------------------------------------------------------
    GIT_REPOSITORY_NOT_FOUND = ErrorCode(_("This project has no Git repository."), status_code=HTTPStatus.NOT_FOUND)
    GIT_REPOSITORY_NOT_READY = ErrorCode(
        _("This project's Git repository is not ready."), status_code=HTTPStatus.CONFLICT
    )
    REPO_SERVER_CONFIGURATION_ERROR = ErrorCode(
        _("Git repository service is not configured correctly. Please contact an administrator."),
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
    )
    REPO_SERVER_UNAVAILABLE = ErrorCode(
        _("Git repository service is unavailable. Please retry later."),
        status_code=HTTPStatus.BAD_GATEWAY,
    )

    # --- Agent Runtime ----------------------------------------------------------------------------
    AGENT_BUSY = ErrorCode(
        _("The Agent Runtime is already executing a run for this conversation."),
        status_code=HTTPStatus.CONFLICT,
    )
    AGENT_WORKSPACE_BUSY = ErrorCode(
        _("Another conversation already has a running Agent on this project."),
        status_code=HTTPStatus.CONFLICT,
    )
    # Says which layer refused and why, because "busy" would send the reader looking for a
    # run that is not there. The Agent's own escape hatch is not offered here yet: exposing
    # "continue without saving this turn" is a product decision, not an error-handling one.
    AGENT_WORKSPACE_SAVE_PENDING = ErrorCode(
        _("The previous turn's files have not been saved to this project's repository yet."),
        status_code=HTTPStatus.CONFLICT,
    )
    AGENT_UNAVAILABLE = ErrorCode(_("The Agent Runtime is unavailable."), status_code=HTTPStatus.BAD_GATEWAY)

    # --- Model access -----------------------------------------------------------------------------
    # Three failures with three different people to fix them: an operator for the settings, the
    # user for their login, and nobody in particular for a token service that is down.
    MODEL_ACCESS_CONFIGURATION_ERROR = ErrorCode(
        _("Model access is not configured correctly. Please contact an administrator."),
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
    )
    # 401 rather than 400: the session still says who the user is, but the BlueKing login the
    # token is exchanged with is gone, and logging in again is what brings it back.
    MODEL_CREDENTIAL_MISSING = ErrorCode(
        _("Your BlueKing login is unavailable. Please log in again."),
        status_code=HTTPStatus.UNAUTHORIZED,
    )
    MODEL_ACCESS_TOKEN_UNAVAILABLE = ErrorCode(
        _("Could not obtain an access token for the model. Please retry later."),
        status_code=HTTPStatus.BAD_GATEWAY,
    )

    # --- Workspace application preview --------------------------------------------------------------
    # Two separate failures, because only the first one is the user's to fix. No Runtime means
    # nothing is serving this conversation yet, which a turn of conversation resolves; an
    # unreachable application means the Runtime is up but what the model wrote is not answering.
    PREVIEW_RUNTIME_NOT_RUNNING = ErrorCode(
        _("This conversation has no running Agent Runtime, so its application cannot be opened."),
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
    )
    PREVIEW_APP_UNREACHABLE = ErrorCode(
        _("This conversation's application is not answering."),
        status_code=HTTPStatus.BAD_GATEWAY,
    )


error_codes = ErrorCodes()
