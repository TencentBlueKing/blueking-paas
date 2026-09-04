"""Replication as a deployment actually gets it: env vars in, a real socket out.

Everything under :mod:`tests.replication` builds a ``StateReplicator`` by hand, which cannot
answer the one question that matters most here -- whether a Runtime assembled from nothing but
``APP_SPARK_AGENT_*`` builds one at all. If that wiring broke, every unit test would still pass
and every conversation would be silently unrecoverable.

The other half is the cold start: a second Runtime, on an empty state directory, handed back
what the first one pushed. That is the whole point of replicating, so it is asserted end to end
against two real processes rather than inferred from the parts.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from app_spark_agent.fake_model import NOTE_FILENAME_TEMPLATE, WRITE_FILE_TOOL
from tests.support import console
from tests.support.control_plane import TOKEN, serve_control_plane
from tests.support.live import LiveRuntime
from tests.support.live_fixtures import StartRuntime

FIRST_NOTE = NOTE_FILENAME_TEMPLATE.format(turn=1)
SECOND_NOTE = NOTE_FILENAME_TEMPLATE.format(turn=2)

# The Runtime flushes before it releases its run guard, so by the time a turn returns the push
# has already happened. This only covers the scheduling slack around that.
SETTLE_TIMEOUT_SECONDS = 10.0


def test_a_runtime_replicates_everything_it_was_configured_to(
    start_runtime: StartRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    with serve_control_plane() as (url, received):
        runtime = start_runtime(
            MODEL="fake:write-file",
            CONTROL_PLANE_URL=url,
            CONTROL_PLANE_TOKEN=TOKEN,
        )

        console.banner("turn 1: the Runtime pushes as it goes")
        turn = runtime.turn(conversation_id=conversation_id, prompt="write my first note")
        assert turn.tool_calls == [WRITE_FILE_TOOL]

        health = _settled(runtime)

        # Every local cursor has an equal on the other side; that is what "replicated" means.
        assert received.seqs("messages") == list(range(1, health["log_seq"] + 1))
        assert received.seqs("ui-events") == list(range(1, health["ui_event_seq"] + 1))
        assert received.context is not None
        assert received.context["context_version"] == health["context_version"]

        # And the Runtime says so itself, which is how a control plane decides it is safe to
        # discard one without reading its files.
        assert health["replicating"] is True
        assert health["pushed_log_seq"] == health["log_seq"]
        assert health["pushed_ui_event_seq"] == health["ui_event_seq"]
        assert health["pushed_context_version"] == health["context_version"]


def test_a_conversation_moves_to_a_runtime_that_starts_from_nothing(
    start_runtime: StartRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    """The cold start, with two real processes and the archived context in between."""
    with serve_control_plane() as (url, received):
        console.banner("first Runtime: one turn, then it goes away entirely")
        first = start_runtime(
            state="first",
            MODEL="fake:write-file",
            CONTROL_PLANE_URL=url,
            CONTROL_PLANE_TOKEN=TOKEN,
        )
        first.turn(conversation_id=conversation_id, prompt="write my first note")
        before = _settled(first)
        first.stop()

        console.banner("second Runtime: an empty state directory, seeded from the archive")
        second = start_runtime(
            state="second",
            MODEL="fake:write-file",
            CONTROL_PLANE_URL=url,
            CONTROL_PLANE_TOKEN=TOKEN,
        )
        assert second.health()["context_version"] == 0, "a genuinely empty state directory"

        archived = received.context
        assert archived is not None, "the first Runtime never pushed its context"
        restored = second.restore(
            archived,
            if_match="0",
            log_seq=before["log_seq"],
            ui_event_seq=before["ui_event_seq"],
        )
        assert restored.status_code == 200, restored.text

        console.banner("turn 2: the replacement continues rather than restarts")
        turn = second.turn(conversation_id=conversation_id, prompt="write my second note")

        # The fake numbers its note by counting the user prompts it was handed, so a second
        # note is proof the first turn came back. A Runtime starting from nothing writes the
        # first note again.
        assert SECOND_NOTE in turn.reply
        assert (workspace / SECOND_NOTE).exists()

        # One flat sequence across two generations, with no entry written twice: the seeded
        # base is what keeps the replacement from colliding with its predecessor at seq 1.
        after = _settled(second)
        assert received.seqs("messages") == list(range(1, after["log_seq"] + 1))
        assert received.seqs("ui-events") == list(range(1, after["ui_event_seq"] + 1))
        assert after["log_seq"] > before["log_seq"]
        assert after["context_version"] > before["context_version"]


def _settled(runtime: LiveRuntime) -> dict[str, Any]:
    """Return the Runtime's health once its replication cursors have caught up."""
    deadline = time.monotonic() + SETTLE_TIMEOUT_SECONDS
    while True:
        health: dict[str, Any] = runtime.health()
        caught_up = (
            health["pushed_log_seq"] == health["log_seq"]
            and health["pushed_ui_event_seq"] == health["ui_event_seq"]
            and health["pushed_context_version"] == health["context_version"]
        )
        if caught_up:
            return health
        if time.monotonic() >= deadline:
            pytest.fail(f"the Runtime never caught up with the control plane: {health}")
        time.sleep(0.05)
