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

"""Receiving a Runtime's pushed state.

The Runtime retries. That is not an edge case here, it is the normal way a batch whose
acknowledgement was lost gets delivered -- so "stored twice" and "stored once" have to be the
same outcome, and a batch that would leave a hole has to be refused loudly enough for the
Runtime to know where to resume.
"""

from __future__ import annotations

from typing import Any

import pytest

from app_spark_api.agent.conversations import state
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.state_models import ConversationMessage
from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db

TIMESTAMP = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def project(bk_user) -> Project:
    return Project.objects.create(
        id="state-storage",
        name="State Storage",
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


@pytest.fixture(autouse=True)
def context_storage(settings, tmp_path) -> None:
    """Archive context blobs under the test's own directory rather than the shared default."""
    settings.AGENT_CONTEXT_STORAGE = {"backend": "host_tmp_path", "root": str(tmp_path / "blobs")}


def messages(*seqs: int, run_id: str = "run-a") -> list[dict[str, Any]]:
    """Build a batch in the shape the Runtime's transcript channel pushes."""
    return [{"seq": seq, "run_id": run_id, "timestamp": TIMESTAMP, "message": {"n": seq}} for seq in seqs]


def ui_events(*seqs: int, run_id: str = "run-a") -> list[dict[str, Any]]:
    """Build a batch in the shape the Runtime's AG-UI channel pushes."""
    return [{"seq": seq, "run_id": run_id, "timestamp": TIMESTAMP, "event": {"type": "CUSTOM"}} for seq in seqs]


# --- Appending -----------------------------------------------------------------------------


def test_an_empty_channel_starts_at_zero(conversation) -> None:
    assert state.last_seq(conversation.id, state.MESSAGE_CHANNEL) == 0


def test_a_batch_advances_the_cursor(conversation) -> None:
    stored = state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 2, 3))

    assert stored == 3
    assert state.last_seq(conversation.id, state.MESSAGE_CHANNEL) == 3


def test_an_empty_batch_is_a_no_op(conversation) -> None:
    state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1))

    assert state.append_records(conversation.id, state.MESSAGE_CHANNEL, []) == 1


def test_the_same_batch_twice_is_stored_once(conversation) -> None:
    """The Runtime retries whenever it did not see the acknowledgement; both answers agree."""
    assert state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 2)) == 2

    assert state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 2)) == 2

    records, _ = _read_messages(conversation.id)
    assert [record["seq"] for record in records] == [1, 2]


def test_a_batch_that_overlaps_what_is_stored_fills_only_the_new_part(conversation) -> None:
    state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 2))

    assert state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(2, 3, 4)) == 4

    records, _ = _read_messages(conversation.id)
    assert [record["seq"] for record in records] == [1, 2, 3, 4]


def test_a_batch_that_would_leave_a_gap_is_refused(conversation) -> None:
    """Storing it would create a hole no later write can fill, so the real cursor is returned."""
    state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1))

    assert state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(5, 6)) == 1

    records, _ = _read_messages(conversation.id)
    assert [record["seq"] for record in records] == [1]


def test_a_batch_with_a_gap_inside_it_is_rejected(conversation) -> None:
    """Unlike a gap at the front, this can only be a caller bug -- the Runtime reads whole pages."""
    with pytest.raises(state.ConversationStateError, match="not contiguous"):
        state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 3))


def test_the_channels_have_separate_cursors(conversation) -> None:
    state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 2, 3))

    assert state.append_records(conversation.id, state.UI_EVENT_CHANNEL, ui_events(1)) == 1
    assert state.last_seq(conversation.id, state.MESSAGE_CHANNEL) == 3


def test_conversations_have_separate_cursors(conversation, other_conversation) -> None:
    """The unique constraint is per conversation, so the same seq exists in both at once."""
    state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1, 2))

    assert state.append_records(other_conversation.id, state.MESSAGE_CHANNEL, messages(1)) == 1
    assert state.last_seq(conversation.id, state.MESSAGE_CHANNEL) == 2


@pytest.mark.parametrize(
    ("batch", "expected"),
    [
        pytest.param([{"run_id": "a", "timestamp": TIMESTAMP, "message": {}}], "seq", id="no-seq"),
        pytest.param([{"seq": 1, "timestamp": TIMESTAMP, "message": {}}], "run_id", id="no-run"),
        pytest.param([{"seq": 1, "run_id": "a", "message": {}}], "timestamp", id="no-timestamp"),
        pytest.param([{"seq": 1, "run_id": "a", "timestamp": TIMESTAMP}], "message", id="no-body"),
        pytest.param(
            [{"seq": 1, "run_id": "a", "timestamp": "yesterday", "message": {}}],
            "ISO-8601",
            id="unparseable-timestamp",
        ),
    ],
)
def test_a_malformed_record_is_rejected(conversation, batch, expected: str) -> None:
    with pytest.raises(state.ConversationStateError, match=expected):
        state.append_records(conversation.id, state.MESSAGE_CHANNEL, batch)


# --- Reading the history back ---------------------------------------------------------------


def test_stored_events_read_back_in_the_runtime_wire_shape(conversation) -> None:
    """A client must not be able to tell stored history from a live stream by its shape."""
    state.append_records(conversation.id, state.UI_EVENT_CHANNEL, ui_events(1))

    records, last = state.read_ui_events(conversation.id, since=0, limit=10)

    assert last == 1
    assert records == [{"seq": 1, "run_id": "run-a", "timestamp": TIMESTAMP, "event": {"type": "CUSTOM"}}]


def test_events_are_paged_from_a_cursor(conversation) -> None:
    state.append_records(conversation.id, state.UI_EVENT_CHANNEL, ui_events(1, 2, 3, 4))

    page, last = state.read_ui_events(conversation.id, since=1, limit=2)

    assert [record["seq"] for record in page] == [2, 3]
    # The cursor is the channel's end, not the page's, so a caller knows more is waiting.
    assert last == 4


def test_reading_past_the_end_yields_nothing(conversation) -> None:
    state.append_records(conversation.id, state.UI_EVENT_CHANNEL, ui_events(1))

    page, last = state.read_ui_events(conversation.id, since=1, limit=10)

    assert page == []
    assert last == 1


# --- Archiving the context --------------------------------------------------------------------


def test_a_context_round_trips_through_the_blob_store(conversation) -> None:
    document = {"schema_version": 3, "context_version": 4, "messages": [{"kind": "request"}]}

    assert state.save_context(conversation.id, document) == 4

    assert state.context_version(conversation.id) == 4
    assert state.load_context(conversation.id) == document


def test_nothing_archived_reads_as_no_context(conversation) -> None:
    assert state.context_version(conversation.id) == 0
    assert state.load_context(conversation.id) is None


def test_a_newer_version_replaces_the_archived_one(conversation) -> None:
    state.save_context(conversation.id, {"context_version": 1, "messages": []})

    assert state.save_context(conversation.id, {"context_version": 2, "messages": ["a"]}) == 2

    assert state.load_context(conversation.id) == {"context_version": 2, "messages": ["a"]}


def test_a_superseded_version_is_accepted_without_overwriting(conversation) -> None:
    """A retry of an older push is expected, and must not undo the newer document."""
    state.save_context(conversation.id, {"context_version": 5, "messages": ["new"]})

    assert state.save_context(conversation.id, {"context_version": 3, "messages": ["old"]}) == 5

    assert state.load_context(conversation.id) == {"context_version": 5, "messages": ["new"]}


@pytest.mark.parametrize("version", [None, -1, "4", True])
def test_a_context_without_a_usable_version_is_rejected(conversation, version) -> None:
    with pytest.raises(state.ConversationStateError, match="context_version"):
        state.save_context(conversation.id, {"context_version": version})


def test_clearing_forgets_everything_about_one_conversation(
    conversation,
    other_conversation,
) -> None:
    state.append_records(conversation.id, state.MESSAGE_CHANNEL, messages(1))
    state.append_records(conversation.id, state.UI_EVENT_CHANNEL, ui_events(1))
    state.save_context(conversation.id, {"context_version": 1, "messages": []})
    state.append_records(other_conversation.id, state.MESSAGE_CHANNEL, messages(1))

    state.clear(conversation.id)

    assert state.last_seq(conversation.id, state.MESSAGE_CHANNEL) == 0
    assert state.last_seq(conversation.id, state.UI_EVENT_CHANNEL) == 0
    assert state.context_version(conversation.id) == 0
    assert state.last_seq(other_conversation.id, state.MESSAGE_CHANNEL) == 1


def _read_messages(conversation_id) -> tuple[list[dict[str, Any]], int]:
    """Read the transcript channel, which has no public read path of its own yet."""
    rows = ConversationMessage.objects.filter(conversation_id=conversation_id).order_by("seq")
    return ([{"seq": row.seq, "message": row.payload} for row in rows], len(rows))
