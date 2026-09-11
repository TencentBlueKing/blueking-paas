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

"""Deciding when a commit and a conversation add up to somewhere worth resuming from.

The two halves arrive over different connections and in either order, so most of what is worth
testing here is the *incomplete* pair: code on the remote with no matching context, and context
with no commit. Neither is a restore point, and mistaking one for a restore point is the failure
this whole mechanism exists to prevent -- a Runtime whose files and whose memory disagree does
not crash, it just quietly writes the wrong code.
"""

from __future__ import annotations

from typing import Any

import pytest

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


def record(conversation: Conversation, *, commit: str, context_version: int, run_id: str = "run-a") -> bool:
    """Report one checkpoint the way the ingest endpoint does, and return what it answered."""
    return checkpoints.record(
        conversation.id,
        run_id=run_id,
        commit=commit,
        tag=f"app-spark/checkpoint/{run_id}",
        context_version=context_version,
        log_seq=0,
        ui_event_seq=0,
        state_epoch=conversation.state_epoch,
    )


class TestRestorability:
    """Only a commit *and* its own context version make somewhere to resume from."""

    def test_a_commit_whose_context_is_archived_is_restorable(self, conversation):
        state.save_context(conversation.id, context(3))

        assert record(conversation, commit="a" * 40, context_version=3) is True
        assert checkpoints.latest_restorable(conversation.id).commit == "a" * 40

    def test_a_commit_without_its_context_is_not(self, conversation):
        """Code pushed, context not saved yet: the row is kept, but it is not a restore point."""
        assert record(conversation, commit="b" * 40, context_version=1) is False
        assert checkpoints.latest_restorable(conversation.id) is None

    def test_a_context_without_a_commit_is_not(self, conversation):
        """The mirror image, and the one a cold start would otherwise silently accept."""
        state.save_context(conversation.id, context(1))

        assert checkpoints.latest_restorable(conversation.id) is None

    def test_a_late_context_makes_an_earlier_commit_restorable(self, conversation):
        """The push won the race. Nothing re-reports the checkpoint; it simply becomes valid."""
        assert record(conversation, commit="c" * 40, context_version=2) is False

        state.save_context(conversation.id, context(2))

        assert checkpoints.latest_restorable(conversation.id).commit == "c" * 40

    def test_a_newer_context_does_not_stand_in_for_the_missing_one(self, conversation):
        """Version 3's document describes turn three, so it cannot vouch for turn two's files."""
        record(conversation, commit="d" * 40, context_version=2, run_id="run-b")
        state.save_context(conversation.id, context(3))

        assert checkpoints.latest_restorable(conversation.id) is None

    def test_the_newest_of_several_is_the_one_offered(self, conversation):
        state.save_context(conversation.id, context(1))
        record(conversation, commit="e" * 40, context_version=1, run_id="run-a")
        state.save_context(conversation.id, context(2))
        record(conversation, commit="f" * 40, context_version=2, run_id="run-b")

        assert checkpoints.latest_restorable(conversation.id).commit == "f" * 40


class TestReReporting:
    """A Runtime whose acknowledgement was lost re-reports; it must not re-commit."""

    def test_reporting_the_same_commit_twice_keeps_one_row(self, conversation):
        state.save_context(conversation.id, context(1))
        record(conversation, commit="a" * 40, context_version=1)

        assert record(conversation, commit="a" * 40, context_version=1) is True
        assert checkpoints.restorable_checkpoints(conversation.id).count() == 1


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
    """Versions are kept per checkpoint, so something has to take the unreferenced ones away."""

    def test_old_unreferenced_versions_are_reclaimed(self, conversation, settings):
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 2

        for version in range(1, 6):
            state.save_context(conversation.id, context(version))

        assert kept_versions(conversation) == {4, 5}

    def test_a_version_a_checkpoint_needs_survives_reclamation(self, conversation, settings):
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 1
        state.save_context(conversation.id, context(1))
        record(conversation, commit="a" * 40, context_version=1)

        for version in range(2, 6):
            state.save_context(conversation.id, context(version))

        # Still restorable, and still restorable to the document that goes with it -- which is
        # the whole reason retention has to know about checkpoints at all.
        assert checkpoints.latest_restorable(conversation.id).commit == "a" * 40
        assert state.load_context_version(conversation.id, 1) == context(1)

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

    def test_dropping_an_old_checkpoint_releases_the_version_it_pinned(self, conversation, settings, tmp_path):
        """Both ends have to be reclaimed. Capping versions alone leaves every pinned blob forever."""
        settings.AGENT_CHECKPOINTS_KEPT = 1
        settings.AGENT_CONTEXT_VERSIONS_KEPT = 1

        state.save_context(conversation.id, context(1))
        record(conversation, commit="a" * 40, context_version=1, run_id="run-a")
        state.save_context(conversation.id, context(2))
        record(conversation, commit="b" * 40, context_version=2, run_id="run-b")
        state.save_context(conversation.id, context(3))

        # Version 1 went in the same pass as the checkpoint that was holding it, which is what
        # reclaiming checkpoints before versions buys.
        assert kept_checkpoints(conversation) == {2}
        assert kept_versions(conversation) == {2, 3}
        assert not (tmp_path / "blobs" / f"{conversation.id}-v1.json").exists()

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
        assert checkpoints.latest_restorable(conversation.id).commit == "a" * 40


class TestVersionedDocuments:
    """Each version keeps its own document, which is what a checkpoint reaches for."""

    def test_an_older_version_is_readable_after_a_newer_one_is_archived(self, conversation):
        state.save_context(conversation.id, context(1))
        state.save_context(conversation.id, context(2))

        assert state.load_context_version(conversation.id, 1) == context(1)
        assert state.load_context_version(conversation.id, 2) == context(2)
        # And the plain cold start still gets the newest, unchanged.
        assert state.load_context(conversation.id) == context(2)

    def test_a_version_that_was_never_archived_reads_as_missing(self, conversation):
        state.save_context(conversation.id, context(1))

        assert state.load_context_version(conversation.id, 7) is None
