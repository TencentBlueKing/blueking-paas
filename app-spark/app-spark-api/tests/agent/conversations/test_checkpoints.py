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

"""Which commit a cold start restores the workspace from, and how long the history is kept.

A checkpoint is decoupled from the conversation's context: the files follow the Project, and the
context injected is always the newest archived one. So the order in which a commit and a context
version arrive must not decide whether the commit can be restored, and retention must not keep
context versions around on a checkpoint's behalf.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.db import transaction

from app_spark_api.agent.conversations import checkpoints, state
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.state_models import (
    ConversationCheckpoint,
    ConversationContextVersion,
)
from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(bk_user) -> Project:
    return Project.objects.create(
        id="checkpoints",
        name="Checkpoints",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )


@pytest.fixture
def conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


@pytest.fixture(autouse=True)
def context_storage(settings, tmp_path) -> None:
    """Archive context blobs under the test's own directory rather than the shared default."""
    settings.AGENT_CONTEXT_STORAGE = {"backend": "host_tmp_path", "root": str(tmp_path / "blobs")}


def context(version: int) -> dict[str, Any]:
    """A context document distinctive enough that the wrong version is recognisable."""
    return {"context_version": version, "messages": [f"turn {version}"]}


def record(
    conversation: Conversation,
    *,
    commit: str,
    context_version: int,
    run_id: str = "run-a",
    completed: bool = True,
) -> None:
    """Report one checkpoint the way the ingest endpoint does."""
    checkpoints.record(
        conversation.id,
        run_id=run_id,
        commit=commit,
        tag=f"app-spark/checkpoint/{run_id}",
        context_version=context_version,
        completed=completed,
        log_seq=0,
        ui_event_seq=0,
        state_epoch=conversation.state_epoch,
    )


def latest_commit(conversation: Conversation) -> str | None:
    checkpoint = checkpoints.latest(conversation.id)
    return None if checkpoint is None else checkpoint.commit


class TestLatest:
    """A reported commit is on the remote, and that alone makes it the one to restore from."""

    def test_a_commit_whose_context_is_archived_is_offered(self, conversation):
        state.save_context(conversation.id, context(3))
        record(conversation, commit="a" * 40, context_version=3)

        assert latest_commit(conversation) == "a" * 40

    def test_a_commit_is_offered_before_its_context_arrives(self, conversation):
        """The push won the race against the context. The files are already on the remote."""
        record(conversation, commit="b" * 40, context_version=1)

        assert latest_commit(conversation) == "b" * 40

    def test_a_context_without_a_commit_offers_nothing(self, conversation):
        """Chat-only turns change no files, so there is nothing to put back."""
        state.save_context(conversation.id, context(1))

        assert latest_commit(conversation) is None

    def test_an_interrupted_commit_is_offered(self, conversation):
        """Its files are on the Project's branch either way; the flag is only a record."""
        state.save_context(conversation.id, context(1))
        record(conversation, commit="9" * 40, context_version=1, run_id="run-interrupted", completed=False)

        assert latest_commit(conversation) == "9" * 40

    def test_a_commit_whose_own_version_was_never_archived_is_offered(self, conversation):
        """Version 2 was skipped, which must not strand the files turn two pushed."""
        record(conversation, commit="d" * 40, context_version=2, run_id="run-b")
        state.save_context(conversation.id, context(3))

        assert latest_commit(conversation) == "d" * 40

    def test_the_newest_of_several_is_the_one_offered(self, conversation):
        state.save_context(conversation.id, context(1))
        record(conversation, commit="e" * 40, context_version=1, run_id="run-a")
        state.save_context(conversation.id, context(2))
        record(conversation, commit="f" * 40, context_version=2, run_id="run-b")

        assert latest_commit(conversation) == "f" * 40

    def test_the_last_reported_wins_even_when_the_context_version_went_backwards(self, conversation):
        """A Runtime lost before its context was archived leaves a successor counting from 0.

        The older Runtime's checkpoint then carries the higher version, yet the newer commit
        is what the conversation pushed last.
        """
        record(conversation, commit="a" * 40, context_version=2, run_id="run-old-runtime")
        record(conversation, commit="b" * 40, context_version=0, run_id="run-new-runtime")

        assert latest_commit(conversation) == "b" * 40


class TestReReporting:
    """A Runtime whose acknowledgement was lost re-reports; it must not re-commit."""

    def test_reporting_the_same_commit_twice_keeps_one_row(self, conversation):
        state.save_context(conversation.id, context(1))
        record(conversation, commit="a" * 40, context_version=1)
        record(conversation, commit="a" * 40, context_version=1)

        assert ConversationCheckpoint.objects.filter(conversation=conversation).count() == 1


def kept_checkpoints(conversation: Conversation) -> set[int]:
    """The context versions of the checkpoints this conversation still has rows for."""
    return set(
        ConversationCheckpoint.objects.filter(conversation=conversation).values_list("context_version", flat=True)
    )


def kept_versions(conversation: Conversation) -> set[int]:
    """The context versions this conversation still has rows for."""
    return set(
        ConversationContextVersion.objects.filter(conversation=conversation).values_list("context_version", flat=True)
    )


class TestRetention:
    """Versions and checkpoints are each capped on their own; neither keeps the other alive."""

    def test_old_versions_are_reclaimed(self, conversation, settings):
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 2

        for version in range(1, 6):
            state.save_context(conversation.id, context(version))

        assert kept_versions(conversation) == {4, 5}

    def test_a_checkpoint_outlives_the_context_version_it_was_made_at(self, conversation, settings):
        """Edit files once, then chat for a while: the files must still come back.

        This is the regression the pairing used to cause. Pinning the checkpoint's version kept
        a blob nothing reads; not pinning it, while still asking for it, stranded the files.
        """
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 1
        state.save_context(conversation.id, context(1))
        record(conversation, commit="a" * 40, context_version=1)

        for version in range(2, 6):
            state.save_context(conversation.id, context(version))

        assert kept_versions(conversation) == {5}
        assert latest_commit(conversation) == "a" * 40

    def test_reclaiming_removes_the_blob_as_well_as_the_row(self, conversation, settings, tmp_path):
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 1
        state.save_context(conversation.id, context(1))
        blob = tmp_path / "blobs" / f"{conversation.id}-v1.json"
        assert blob.exists()

        state.save_context(conversation.id, context(2))

        assert not blob.exists()

    def test_only_the_most_recent_checkpoints_are_kept(self, conversation, settings):
        settings.AGENT_CHECKPOINTS_KEPT = 2

        for version in range(1, 5):
            state.save_context(conversation.id, context(version))
            record(conversation, commit=str(version) * 40, context_version=version, run_id=f"run-{version}")
        # Reclamation rides along with archiving, so the last checkpoint reported is only taken
        # into account by the pass that the next context push triggers.
        state.save_context(conversation.id, context(5))

        assert kept_checkpoints(conversation) == {3, 4}

    def test_retention_keeps_the_last_reported_even_when_the_context_version_went_backwards(
        self, conversation, settings
    ):
        settings.AGENT_CHECKPOINTS_KEPT = 1
        record(conversation, commit="a" * 40, context_version=2, run_id="run-old-runtime")
        record(conversation, commit="b" * 40, context_version=0, run_id="run-new-runtime")

        checkpoints.reclaim(conversation.id)

        assert set(
            ConversationCheckpoint.objects.filter(conversation=conversation).values_list("commit", flat=True)
        ) == {"b" * 40}

    def test_the_newest_version_survives_the_most_aggressive_retention(self, conversation, settings):
        """Keeping nothing would delete what a cold start reads, so both caps are floored at one."""
        settings.AGENT_CHECKPOINTS_KEPT = 0
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 0

        state.save_context(conversation.id, context(1))
        state.save_context(conversation.id, context(2))
        record(conversation, commit="a" * 40, context_version=2)

        assert kept_versions(conversation) == {2}
        assert state.context_version(conversation.id) == 2
        assert state.load_context(conversation.id) == context(2)
        assert latest_commit(conversation) == "a" * 40

    def test_registration_and_retention_take_the_same_conversation_lock(
        self,
        conversation,
        monkeypatch,
    ):
        calls: list[tuple[str, Any]] = []
        lock_in_state = state._lock_conversation
        lock_in_checkpoints = checkpoints._lock_conversation

        def observe_state_lock(conversation_id: Any) -> None:
            assert transaction.get_connection().in_atomic_block
            calls.append(("state", conversation_id))
            lock_in_state(conversation_id)

        def observe_checkpoint_lock(conversation_id: Any) -> None:
            assert transaction.get_connection().in_atomic_block
            calls.append(("checkpoint", conversation_id))
            lock_in_checkpoints(conversation_id)

        monkeypatch.setattr(state, "_lock_conversation", observe_state_lock)
        monkeypatch.setattr(checkpoints, "_lock_conversation", observe_checkpoint_lock)

        state.save_context(conversation.id, context(1))
        record(conversation, commit="a" * 40, context_version=1)

        assert calls == [
            ("state", conversation.id),
            ("checkpoint", conversation.id),
            ("checkpoint", conversation.id),
        ]


class TestVersionedDocuments:
    """Each version keeps its own document, so archiving a newer one never overwrites an older one."""

    def test_an_older_version_keeps_its_own_document_after_a_newer_one_is_archived(self, conversation):
        state.save_context(conversation.id, context(1))
        state.save_context(conversation.id, context(2))

        assert stored_document(conversation, 1) == context(1)
        assert stored_document(conversation, 2) == context(2)
        # And the cold start gets the newest, unchanged.
        assert state.load_context(conversation.id) == context(2)


def stored_document(conversation: Conversation, version: int) -> dict[str, Any]:
    """Read back the blob one archived version row points at."""
    row = ConversationContextVersion.objects.get(conversation=conversation, context_version=version)
    return json.loads(row.get_blob_store().get_bytes())
