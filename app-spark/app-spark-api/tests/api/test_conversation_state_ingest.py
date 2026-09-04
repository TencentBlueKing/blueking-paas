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

"""The endpoints an Agent Runtime pushes its state through.

These are reachable without a logged-in user, so the interesting question is not what a correct
push does -- ``tests/agent/conversations/test_state.py`` covers the storage -- but who is
allowed to make one. A token names exactly one conversation, and holding somebody else's
address must not be enough to write into it.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.test import Client

from app_spark_api.agent.conversations import services, state
from app_spark_api.agent.conversations.internal_api import state_ingest_path
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.tokens import mint_state_token
from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db

TIMESTAMP = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def project(bk_user) -> Project:
    return Project.objects.create(
        id="state-ingest",
        name="State Ingest",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )


@pytest.fixture
def conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


@pytest.fixture
def other_conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


@pytest.fixture
def runtime(conversation) -> RuntimeCaller:
    """A caller holding the token this conversation's Runtime was spawned with."""
    return RuntimeCaller(conversation)


@pytest.fixture(autouse=True)
def context_storage(settings, tmp_path) -> None:
    """Archive context blobs under the test's own directory rather than the shared default."""
    settings.AGENT_CONTEXT_STORAGE = {"backend": "host_tmp_path", "root": str(tmp_path / "blobs")}


class RuntimeCaller:
    """Drives the ingest endpoints the way a spawned Runtime does.

    :param conversation: Conversation whose state is being pushed.
    :param token: Token to present, defaulting to the one this conversation's Runtime is given.
    """

    def __init__(self, conversation: Conversation, token: str | None = None) -> None:
        self.conversation = conversation
        self.root = state_ingest_path(conversation.id)
        self.client = Client()
        if token is None:
            token = mint_state_token(conversation.id, epoch=conversation.state_epoch)
        self.token = token

    def post(self, channel: str, records: list[dict[str, Any]]) -> Any:
        return self.client.post(
            f"{self.root}{channel}",
            data=json.dumps({"records": records}),
            content_type="application/json",
            headers=self._headers(),
        )

    def put_context(self, document: Any) -> Any:
        return self.client.put(
            f"{self.root}context",
            data=json.dumps(document),
            content_type="application/json",
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


def messages(*seqs: int) -> list[dict[str, Any]]:
    return [{"seq": seq, "run_id": "run-a", "timestamp": TIMESTAMP, "message": {"n": seq}} for seq in seqs]


def ui_events(*seqs: int) -> list[dict[str, Any]]:
    return [{"seq": seq, "run_id": "run-a", "timestamp": TIMESTAMP, "event": {"type": "CUSTOM"}} for seq in seqs]


# --- Pushing -------------------------------------------------------------------------------


def test_a_pushed_batch_is_acknowledged_with_the_new_cursor(runtime: RuntimeCaller) -> None:
    response = runtime.post("messages", messages(1, 2))

    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == {"last_seq": 2}
    assert state.last_seq(runtime.conversation.id, state.MESSAGE_CHANNEL) == 2


def test_the_two_channels_are_separate_endpoints(runtime: RuntimeCaller) -> None:
    assert runtime.post("messages", messages(1, 2)).status_code == HTTPStatus.OK

    response = runtime.post("ui-events", ui_events(1))

    assert json.loads(response.content) == {"last_seq": 1}
    assert state.last_seq(runtime.conversation.id, state.MESSAGE_CHANNEL) == 2


def test_a_redelivered_batch_is_acknowledged_the_same_way(runtime: RuntimeCaller) -> None:
    """This is what makes the Runtime free to retry whenever an answer goes missing."""
    first = runtime.post("messages", messages(1, 2))

    second = runtime.post("messages", messages(1, 2))

    assert json.loads(second.content) == json.loads(first.content) == {"last_seq": 2}


def test_a_batch_that_would_leave_a_gap_is_answered_with_the_real_cursor(
    runtime: RuntimeCaller,
) -> None:
    """The answer is what the Runtime rewinds to, so it has to be the truth, not the request."""
    runtime.post("messages", messages(1))

    response = runtime.post("messages", messages(9, 10))

    assert json.loads(response.content) == {"last_seq": 1}


def test_a_malformed_record_is_refused(runtime: RuntimeCaller) -> None:
    response = runtime.post("messages", [{"seq": 0, "run_id": "a", "timestamp": TIMESTAMP}])

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_a_context_document_is_archived_as_it_arrived(runtime: RuntimeCaller) -> None:
    """Stored verbatim: this service does not need to understand the Runtime's schema, and a
    validation of its own here would have to be kept in step with every change to it."""
    document = {"schema_version": 3, "context_version": 4, "messages": [{"kind": "request"}]}

    response = runtime.put_context(document)

    assert json.loads(response.content) == {"context_version": 4}
    assert state.load_context(runtime.conversation.id) == document


def test_a_context_without_a_version_is_refused(runtime: RuntimeCaller) -> None:
    response = runtime.put_context({"messages": []})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_a_context_body_that_is_not_an_object_is_refused(runtime: RuntimeCaller) -> None:
    response = runtime.put_context([1, 2])

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_a_context_larger_than_djangos_default_body_limit_is_still_archived(
    runtime: RuntimeCaller,
) -> None:
    """A real context runs to megabytes; Django refuses bodies over 2.5MB unless told otherwise.

    Worth its own test because the failure is silent rather than loud: ``request.body`` raises
    ``RequestDataTooBig``, the endpoint answers 400, and the Runtime files that under "retry
    later" and keeps retrying forever. Nothing surfaces except a growing replication lag, and
    the conversation's only cold-start source never lands.
    """
    filler = "x" * (3 * 1024 * 1024)
    document = {"schema_version": 3, "context_version": 1, "messages": [{"text": filler}]}

    response = runtime.put_context(document)

    assert response.status_code == HTTPStatus.OK, response.content[:200]
    assert json.loads(response.content) == {"context_version": 1}
    stored = state.load_context(runtime.conversation.id)
    assert stored is not None
    assert stored["messages"][0]["text"] == filler


def test_a_message_batch_larger_than_djangos_default_body_limit_is_still_stored(
    runtime: RuntimeCaller,
) -> None:
    """The same limit applies to the append endpoints, which carry whole model messages."""
    filler = "y" * (1024 * 1024)
    batch = [{"seq": seq, "run_id": "run-a", "timestamp": TIMESTAMP, "message": {"text": filler}} for seq in (1, 2, 3)]

    response = runtime.post("messages", batch)

    assert response.status_code == HTTPStatus.OK, response.content[:200]
    assert json.loads(response.content) == {"last_seq": 3}


# --- Who is allowed to push ------------------------------------------------------------------


def test_an_unauthenticated_push_is_refused(conversation) -> None:
    caller = RuntimeCaller(conversation, token="")

    assert caller.post("messages", messages(1)).status_code == HTTPStatus.UNAUTHORIZED


def test_a_forged_token_is_refused(conversation) -> None:
    caller = RuntimeCaller(conversation, token=f"{conversation.id}:not-a-signature")

    assert caller.post("messages", messages(1)).status_code == HTTPStatus.UNAUTHORIZED


def test_a_token_for_another_conversation_cannot_write_into_this_one(
    conversation,
    other_conversation,
) -> None:
    """A Runtime that learns somebody else's address still holds only its own token."""
    caller = RuntimeCaller(
        other_conversation,
        token=mint_state_token(conversation.id, epoch=conversation.state_epoch),
    )

    response = caller.post("messages", messages(1))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert state.last_seq(other_conversation.id, state.MESSAGE_CHANNEL) == 0


def test_a_token_for_a_conversation_that_is_gone_writes_nothing(conversation) -> None:
    caller = RuntimeCaller(conversation)
    conversation.delete()

    assert caller.post("messages", messages(1)).status_code == HTTPStatus.NOT_FOUND


def test_a_revoked_token_can_no_longer_write(conversation) -> None:
    """A Runtime this service lost track of keeps a valid signature, so it needs cutting off.

    The process may well still be alive and still pushing -- terminating it is best-effort --
    which is exactly why the epoch, and not the provider's bookkeeping, is what decides.
    """
    stale = RuntimeCaller(conversation)
    assert stale.post("messages", messages(1)).status_code == HTTPStatus.OK

    async_to_sync(services.revoke_state_access)(conversation)

    assert stale.post("messages", messages(2)).status_code == HTTPStatus.NOT_FOUND
    assert stale.put_context({"context_version": 1}).status_code == HTTPStatus.NOT_FOUND
    # Refused, not merely unacknowledged: nothing of the revoked generation got in.
    assert state.last_seq(conversation.id, state.MESSAGE_CHANNEL) == 1


def test_a_replacement_runtime_is_authorized_after_a_revocation(conversation) -> None:
    """Revoking must cut off the old generation without locking the conversation itself."""
    async_to_sync(services.revoke_state_access)(conversation)

    fresh = RuntimeCaller(conversation)

    assert fresh.post("messages", messages(1)).status_code == HTTPStatus.OK


def test_a_logged_in_user_has_no_reason_to_reach_this_and_cannot(api_client, conversation) -> None:
    """Session auth is not enough: these endpoints only ever answer to a Runtime's token."""
    response = api_client.post(
        f"{state_ingest_path(conversation.id)}messages",
        data=json.dumps({"records": messages(1)}),
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
