"""Cursor bookkeeping: what survives a restart, and what refuses to go backwards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app_spark_agent.state import Channel, CursorStateError, CursorStore


def make_store(tmp_path: Path) -> CursorStore:
    return CursorStore(tmp_path / "cursors.json")


def test_an_absent_document_reads_as_the_start_of_a_conversation(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    assert store.channel(Channel.MESSAGE).base_seq == 0
    assert store.channel(Channel.MESSAGE).pushed_seq == 0
    assert store.pushed_context_version == 0
    # Nothing is written until something is actually recorded.
    assert not store.path.exists()


async def test_cursors_survive_a_restart(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    await store.rebase({Channel.MESSAGE: 40, Channel.UI_EVENT: 55})
    await store.record_push(Channel.MESSAGE, seq=42)
    await store.record_context_push(7)

    reopened = make_store(tmp_path)

    assert reopened.channel(Channel.MESSAGE).base_seq == 40
    assert reopened.channel(Channel.MESSAGE).pushed_seq == 42
    assert reopened.channel(Channel.UI_EVENT).base_seq == 55
    assert reopened.pushed_context_version == 7


async def test_a_rebase_marks_everything_below_the_base_as_pushed(tmp_path: Path) -> None:
    """The base came from the control plane, so by definition it already holds that much."""
    store = make_store(tmp_path)

    await store.rebase({Channel.MESSAGE: 40})

    assert store.channel(Channel.MESSAGE).pushed_seq == 40


async def test_a_rebase_never_lowers_what_was_already_pushed(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    await store.record_push(Channel.MESSAGE, seq=42)

    await store.rebase({Channel.MESSAGE: 40})

    assert store.channel(Channel.MESSAGE).pushed_seq == 42


async def test_a_rebase_leaves_the_channels_it_was_not_given_alone(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    await store.rebase({Channel.UI_EVENT: 55})

    await store.rebase({Channel.MESSAGE: 40})

    assert store.channel(Channel.UI_EVENT).base_seq == 55


@pytest.mark.parametrize("replayed", [10, 41])
async def test_a_replayed_batch_cannot_undo_progress(tmp_path: Path, replayed: int) -> None:
    """A retry re-sends entries the control plane already had; that is not a reason to rewind."""
    store = make_store(tmp_path)
    await store.record_push(Channel.MESSAGE, seq=42)

    await store.record_push(Channel.MESSAGE, seq=replayed)

    assert store.channel(Channel.MESSAGE).pushed_seq == 42


async def test_a_superseded_context_version_is_ignored(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    await store.record_context_push(7)

    await store.record_context_push(3)

    assert store.pushed_context_version == 7


async def test_channels_do_not_share_a_cursor(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    await store.record_push(Channel.MESSAGE, seq=42)

    assert store.channel(Channel.UI_EVENT).pushed_seq == 0


def test_an_unreadable_document_is_refused_rather_than_reset(tmp_path: Path) -> None:
    """Starting over from zero would re-push a whole conversation and hide the real problem."""
    path = tmp_path / "cursors.json"
    path.write_text(json.dumps({"schema_version": 1, "pushed_context_version": -1}))

    with pytest.raises(CursorStateError, match="invalid cursor document"):
        CursorStore(path)


def test_a_document_from_an_unknown_schema_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "cursors.json"
    path.write_text(json.dumps({"schema_version": 99, "channels": {}}))

    with pytest.raises(CursorStateError):
        CursorStore(path)
