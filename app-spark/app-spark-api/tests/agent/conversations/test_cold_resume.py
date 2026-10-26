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

"""What a cold start hands a fresh Runtime, decided from what this service has stored.

The Runtime is a recording stand-in here: these are questions about which of the stored halves
-- files, context, cursors -- are sent, and none of them needs a real agent to answer. The
end-to-end versions, with a real Runtime destroyed and replaced, are in
``tests/api/test_conversations.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import attrs
import pytest

from app_spark_api.agent.conversations import checkpoints
from app_spark_api.agent.conversations import services as conversation_services
from app_spark_api.agent.conversations import state as conversation_state
from app_spark_api.agent.runtime.entities import RuntimeHealth
from app_spark_api.core.projects.models import Project

if TYPE_CHECKING:
    from app_spark_api.agent.conversations.models import Conversation

pytestmark = pytest.mark.django_db(transaction=True)

TIMESTAMP = "2026-01-01T00:00:00+00:00"

COLD_HEALTH = RuntimeHealth(
    model="fake:test",
    conversation_id=None,
    context_version=0,
    log_seq=0,
    ui_event_seq=0,
    running=False,
    replication_pending=False,
)


@attrs.define
class RecordingClient:
    """Stands in for ``AgentRuntimeClient``, recording what a cold start sends it."""

    workspaces: list[str] = attrs.field(factory=list)
    contexts: list[tuple[dict[str, Any], int, int]] = attrs.field(factory=list)
    cursors: list[tuple[int, int]] = attrs.field(factory=list)

    async def restore_workspace(self, commit: str) -> str:
        self.workspaces.append(commit)
        return "restored"

    async def restore_context(
        self,
        document: dict[str, Any],
        *,
        if_match: int,
        log_seq: int,
        ui_event_seq: int,
    ) -> int:
        assert if_match == 0
        self.contexts.append((document, log_seq, ui_event_seq))
        return document["context_version"]

    async def restore_cursors(self, *, log_seq: int, ui_event_seq: int) -> None:
        self.cursors.append((log_seq, ui_event_seq))

    @property
    def touched(self) -> bool:
        return bool(self.workspaces or self.contexts or self.cursors)


@pytest.fixture(autouse=True)
def context_storage(settings, tmp_path) -> None:
    """Archive context blobs under the test's own directory rather than the shared default."""
    settings.AGENT_CONTEXT_STORAGE = {"backend": "host_tmp_path", "root": str(tmp_path / "contexts")}


@pytest.fixture
def project(bk_user) -> Project:
    return Project.objects.create(
        id="cold-resume",
        name="Cold Resume",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )


@pytest.fixture
async def conversation(project, bk_user) -> Conversation:
    return await conversation_services.create_conversation(project, owner=bk_user.pk)


async def store_entries(conversation: Conversation, *, log_seq: int, ui_event_seq: int) -> None:
    """Store a channel history as an earlier Runtime would have pushed it."""
    messages = [
        {"seq": seq, "run_id": "first-run", "timestamp": TIMESTAMP, "message": {"n": seq}}
        for seq in range(1, log_seq + 1)
    ]
    events = [
        {"seq": seq, "run_id": "first-run", "timestamp": TIMESTAMP, "event": {"type": "CUSTOM"}}
        for seq in range(1, ui_event_seq + 1)
    ]
    await conversation_state.aappend_records(conversation.id, conversation_state.MESSAGE_CHANNEL, messages)
    await conversation_state.aappend_records(conversation.id, conversation_state.UI_EVENT_CHANNEL, events)


async def record_checkpoint(conversation: Conversation, *, context_version: int, completed: bool = True) -> str:
    commit = "a" * 40
    await checkpoints.arecord(
        conversation.id,
        run_id="run-1",
        commit=commit,
        tag="app-spark/checkpoint/run-1",
        context_version=context_version,
        completed=completed,
        log_seq=0,
        ui_event_seq=0,
        state_epoch=conversation.state_epoch,
    )
    return commit


async def resume(conversation: Conversation, client: RecordingClient, health: RuntimeHealth = COLD_HEALTH):
    return await conversation_services._resume_if_cold(conversation, client, health)  # type: ignore[arg-type]


# --- Files and context ---------------------------------------------------------------------


async def test_the_latest_checkpoint_comes_back_with_the_newest_context(conversation):
    """A chat-only turn after the last file change moves the context ahead of the files."""
    await conversation_state.asave_context(conversation.id, {"context_version": 1, "messages": ["turn-1"]})
    commit = await record_checkpoint(conversation, context_version=1)
    newest = {"context_version": 2, "messages": ["turn-1", "turn-2"]}
    await conversation_state.asave_context(conversation.id, newest)
    client = RecordingClient()

    health = await resume(conversation, client)

    assert client.workspaces == [commit]
    assert client.contexts == [(newest, 0, 0)]
    assert health.context_version == 2


async def test_a_conversation_without_checkpoints_only_gets_its_context(conversation):
    document = {"context_version": 1, "messages": []}
    await conversation_state.asave_context(conversation.id, document)
    client = RecordingClient()

    health = await resume(conversation, client)

    assert client.workspaces == []
    assert client.contexts == [(document, 0, 0)]
    assert health.context_version == 1


async def test_a_commit_whose_own_context_never_arrived_is_still_restored(conversation):
    """An interrupted turn pushed its files, but its context never arrived.

    Its commit is on the Project's branch regardless, so it is restored from, alongside the
    newest context that was archived -- here the one from before that turn.
    """
    document = {"context_version": 1, "messages": []}
    await conversation_state.asave_context(conversation.id, document)
    commit = await record_checkpoint(conversation, context_version=2, completed=False)
    client = RecordingClient()

    restored = await conversation_services._restore_files(conversation, client)  # type: ignore[arg-type]

    assert client.workspaces == [commit]
    assert restored == document


# --- Cursors without a context -------------------------------------------------------------


async def test_entries_without_any_context_still_seed_the_numbering(conversation):
    """The first turn's entries arrived but its context never did, and its files did.

    The channels are pushed before the context, so a Runtime lost during the first turn leaves
    exactly this. Starting the replacement at seq 1 would have the ingest drop its first entries
    as redeliveries of the ones already stored.
    """
    await store_entries(conversation, log_seq=3, ui_event_seq=5)
    commit = await record_checkpoint(conversation, context_version=1, completed=False)
    client = RecordingClient()

    health = await resume(conversation, client)

    assert client.workspaces == [commit]
    assert client.contexts == []
    assert client.cursors == [(3, 5)]
    assert (health.context_version, health.log_seq, health.ui_event_seq) == (0, 3, 5)


async def test_a_conversation_with_nothing_stored_is_left_alone(conversation):
    client = RecordingClient()

    health = await resume(conversation, client)

    assert not client.touched
    assert health == COLD_HEALTH


@pytest.mark.parametrize(
    "health",
    [
        pytest.param(attrs.evolve(COLD_HEALTH, log_seq=2), id="transcript-written"),
        pytest.param(attrs.evolve(COLD_HEALTH, ui_event_seq=2), id="ui-events-written"),
    ],
)
async def test_a_runtime_with_entries_of_its_own_is_not_cold(conversation, health):
    """A first turn that failed before committing a context still reads as version 0.

    That Runtime has numbered entries already, so it can no longer be renumbered -- trying would
    only get the turn refused -- and it is continuing its own history, not someone else's.
    """
    # Everything a cold start could restore is here, so only the Runtime's own state can be
    # what keeps it from being sent.
    await store_entries(conversation, log_seq=2, ui_event_seq=2)
    await conversation_state.asave_context(conversation.id, {"context_version": 1, "messages": []})
    await record_checkpoint(conversation, context_version=1)
    client = RecordingClient()

    assert await resume(conversation, client, health) == health
    assert not client.touched
