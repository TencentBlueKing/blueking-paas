"""What the replicator sends, when it gives up, and what it does after it fails.

The control plane is faked in-process (see ``conftest``) so these can assert on the exact
batches that went out. What is deliberately *not* faked is the state: real files, real cursors,
real byte offsets, because the whole design rests on the files being the outbox.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic_ai import ModelMessage
from pydantic_ai.messages import ModelRequest, UserPromptPart

from app_spark_agent.state import AppendLog, ChangeSignal, Channel, ContextStore, CursorStore
from tests.replication.conftest import FakeControlPlane, Harness, make_replicator

CONVERSATION_ID = "11111111-1111-1111-1111-111111111111"

# Generous: none of these tests actually wait for it, they wait for the flush to return.
FLUSH_TIMEOUT = 5.0


def make_messages(text: str) -> list[ModelMessage]:
    return [ModelRequest(parts=[UserPromptPart(content=text)], conversation_id=CONVERSATION_ID)]


async def until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    """Wait for a background pass to have had its effect, or say that it never did."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition():
        if loop.time() >= deadline:
            pytest.fail(f"the replicator never caught up within {timeout}s")
        await asyncio.sleep(0.01)


# --- Flushing ------------------------------------------------------------------------------


async def test_a_flush_pushes_everything_that_was_committed(harness: Harness) -> None:
    await harness.transcript.append("run-a", [{"n": 1}, {"n": 2}, {"n": 3}])
    await harness.ui_events.append("run-a", [{"type": "RUN_STARTED"}])
    await harness.context_store.commit(make_messages("hello"), conversation_id=CONVERSATION_ID)

    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.seqs("messages") == [1, 2, 3]
    assert harness.control_plane.seqs("ui-events") == [1]
    assert harness.control_plane.context is not None
    assert harness.control_plane.context["context_version"] == 1


async def test_a_long_channel_goes_out_in_batches(harness: Harness) -> None:
    """A whole transcript in one request would be tens of megabytes on the wire."""
    await harness.transcript.append("run-a", [{"n": index} for index in range(5)])

    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    # Five entries at a batch size of two: the short final batch is what tells the replicator
    # the channel is drained.
    assert harness.control_plane.batches("messages") == [2, 2, 1]
    assert harness.control_plane.seqs("messages") == [1, 2, 3, 4, 5]


async def test_a_flush_with_nothing_outstanding_sends_nothing(harness: Harness) -> None:
    await harness.transcript.append("run-a", [{"n": 1}])
    await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)
    harness.control_plane.calls.clear()

    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.calls == []


async def test_a_failed_flush_is_reported_without_losing_the_entries(harness: Harness) -> None:
    """A control plane that is down must not fail the run, and must not lose a turn either."""
    await harness.transcript.append("run-a", [{"n": 1}])
    harness.control_plane.failures = 1

    assert not await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.seqs("messages") == []
    assert harness.replicator.pushed_seq(Channel.MESSAGE) == 0
    # The flag is back up, so the background task will come round to it.
    assert harness.signal.raised

    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)
    assert harness.control_plane.seqs("messages") == [1]


# --- The context, which is replaced rather than appended -----------------------------------


async def test_only_the_newest_context_version_is_transferred(harness: Harness) -> None:
    """Coalescing, not queueing: a superseded version is megabytes nobody will ever read."""
    for text in ("one", "two", "three"):
        await harness.context_store.commit(make_messages(text), conversation_id=CONVERSATION_ID)

    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.batches("context") == [0]
    assert harness.control_plane.context is not None
    assert harness.control_plane.context["context_version"] == 3
    assert harness.replicator.pushed_context_version == 3


async def test_an_unchanged_context_is_not_resent(harness: Harness) -> None:
    await harness.context_store.commit(make_messages("hello"), conversation_id=CONVERSATION_ID)
    await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)
    harness.control_plane.calls.clear()

    await harness.transcript.append("run-a", [{"n": 1}])
    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.batches("context") == []


# --- Recovering from a control plane that disagrees ----------------------------------------


async def test_a_batch_that_arrives_twice_is_stored_once(
    harness: Harness,
    tmp_path: Path,
) -> None:
    """Re-sending is how a lost acknowledgement is recovered from, so it has to be harmless."""
    await harness.transcript.append("run-a", [{"n": 1}, {"n": 2}])
    await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    # A cursor document that never recorded the push, the way a crash between sending the batch
    # and writing the cursor would leave one.
    replayed = make_replicator(
        harness.control_plane,
        cursors=CursorStore(tmp_path / "rewound.json"),
        signal=ChangeSignal(),
        channels={Channel.MESSAGE: harness.transcript},
        context_store=harness.context_store,
    )
    try:
        assert await replayed.flush(timeout_seconds=FLUSH_TIMEOUT)
    finally:
        await replayed.aclose()

    assert harness.control_plane.seqs("messages") == [1, 2]


async def test_a_control_plane_that_lost_entries_is_sent_them_again(harness: Harness) -> None:
    """It answers with what it holds, so a cursor that ran ahead of it can be walked back.

    One flush has to be enough. ``finish_response`` calls it exactly once per turn, and an idle
    conversation produces no further append to wake the background task with -- so a gap left
    for "the next pass" is a gap that stays open.
    """
    harness.control_plane.truncate_once["messages"] = 1
    await harness.transcript.append("run-a", [{"n": 1}, {"n": 2}])

    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.seqs("messages") == [1, 2]
    assert harness.replicator.pushed_seq(Channel.MESSAGE) == 2


async def test_a_flush_that_could_not_close_the_gap_says_so(harness: Harness) -> None:
    """A control plane that drops every batch it accepts must not be reported as caught up."""
    harness.control_plane.truncate_to["messages"] = 1
    await harness.transcript.append("run-a", [{"n": 1}, {"n": 2}])

    assert not await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.seqs("messages") == [1]
    assert harness.replicator.pushed_seq(Channel.MESSAGE) < 2
    # The flag is back up, so the background task keeps working at it.
    assert harness.signal.raised

    harness.control_plane.truncate_to.clear()
    assert await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.control_plane.seqs("messages") == [1, 2]


async def test_a_context_the_control_plane_never_took_is_not_recorded_as_pushed(
    harness: Harness,
) -> None:
    """The context is the whole of what a cold start restores, so its lag has to be reported."""
    harness.control_plane.context_ceiling = 0
    await harness.context_store.commit(make_messages("hello"), conversation_id=CONVERSATION_ID)

    assert not await harness.replicator.flush(timeout_seconds=FLUSH_TIMEOUT)

    assert harness.replicator.pushed_context_version == 0
    assert harness.signal.raised


# --- The background task -------------------------------------------------------------------


async def test_the_background_task_catches_up_on_its_own(harness: Harness) -> None:
    """The run path only raises a flag; nothing about a turn waits on the network."""
    await harness.replicator.start()

    await harness.transcript.append("run-a", [{"n": 1}])
    await until(lambda: harness.control_plane.seqs("messages") == [1])

    await harness.transcript.append("run-b", [{"n": 2}])
    await until(lambda: harness.control_plane.seqs("messages") == [1, 2])


async def test_the_background_task_retries_after_a_failure(harness: Harness) -> None:
    harness.control_plane.failures = 2
    await harness.transcript.append("run-a", [{"n": 1}])

    await harness.replicator.start()

    await until(lambda: harness.control_plane.seqs("messages") == [1])


async def test_starting_picks_up_what_an_earlier_incarnation_left_behind(
    tmp_path: Path,
    control_plane: FakeControlPlane,
) -> None:
    """Nothing else would wake the task: the conversation may simply never be continued."""
    signal = ChangeSignal()
    transcript = AppendLog(tmp_path / "log.jsonl", payload_key="message", signal=signal)
    await transcript.append("run-a", [{"n": 1}])
    replicator = make_replicator(
        control_plane,
        cursors=CursorStore(tmp_path / "cursors.json"),
        signal=signal,
        channels={Channel.MESSAGE: transcript},
        context_store=ContextStore(tmp_path / "context.json", signal=signal),
    )
    # As if the append had happened in a process that has since exited.
    signal.clear()

    await replicator.start()
    try:
        await until(lambda: control_plane.seqs("messages") == [1])
    finally:
        await replicator.aclose()


# --- Continuing a conversation another Runtime began ---------------------------------------


async def test_a_rebased_channel_pushes_the_numbers_it_continues_from(
    tmp_path: Path,
    control_plane: FakeControlPlane,
) -> None:
    """The cold-start case: a replacement Runtime must not re-send the conversation from 1."""
    signal = ChangeSignal()
    cursors = CursorStore(tmp_path / "cursors.json")
    transcript = AppendLog(tmp_path / "log.jsonl", payload_key="message", signal=signal)
    transcript.rebase(40)
    await cursors.rebase({Channel.MESSAGE: 40})
    await transcript.append("run-b", [{"n": 1}, {"n": 2}])

    replicator = make_replicator(
        control_plane,
        cursors=cursors,
        signal=signal,
        channels={Channel.MESSAGE: transcript},
        context_store=ContextStore(tmp_path / "context.json", signal=signal),
    )
    try:
        assert await replicator.flush(timeout_seconds=FLUSH_TIMEOUT)
    finally:
        await replicator.aclose()

    # Only this incarnation's own entries go out; 1..40 are already on the control plane, which
    # is exactly what the rebase recorded.
    assert control_plane.seqs("messages") == [41, 42]
    assert control_plane.batches("messages") == [2]
