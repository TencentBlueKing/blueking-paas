"""Append-only channel behavior: contiguity, cursors, and crash recovery."""

import json
from pathlib import Path

import pytest

from app_spark_agent.state import AppendLog, AppendLogError, ChangeSignal


def make_log(tmp_path: Path) -> AppendLog:
    return AppendLog(tmp_path / "channel.jsonl", payload_key="message")


async def test_append_assigns_contiguous_sequence_numbers(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    assert log.last_seq == 0

    assert await log.append("run-a", [{"n": 1}, {"n": 2}]) == 2
    assert await log.append("run-b", [{"n": 3}]) == 3
    assert await log.append("run-b", []) == 3

    assert [record.seq for record in log.read_since(0, 10)] == [1, 2, 3]
    assert [record.run_id for record in log.read_since(0, 10)] == ["run-a", "run-a", "run-b"]


async def test_read_since_pages_from_a_cursor(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": index} for index in range(5)])

    page = log.read_since(1, 2)
    assert [record.seq for record in page] == [2, 3]
    assert [record.payload for record in page] == [{"n": 1}, {"n": 2}]
    assert log.read_since(5, 10) == []
    assert log.dump(page)[0] == {
        "seq": 2,
        "run_id": "run-a",
        "timestamp": page[0].timestamp,
        "message": {"n": 1},
    }


async def test_run_index_survives_a_restart(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": 1}])

    reopened = make_log(tmp_path)
    assert reopened.last_seq == 1
    assert reopened.has_run("run-a")
    assert not reopened.has_run("run-b")


async def test_an_interrupted_append_is_discarded_on_load(tmp_path: Path) -> None:
    """A torn final line can only be a crash mid-append, so the durable prefix wins."""
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": 1}])
    with log.path.open("ab") as handle:
        handle.write(b'{"seq":2,"run_id":"run-a","timestamp":"2026-01-01T00:00:00+00:00","mes')

    reopened = make_log(tmp_path)
    assert reopened.last_seq == 1
    assert reopened.path.read_text().splitlines() == [
        json.dumps(
            {
                "seq": 1,
                "run_id": "run-a",
                "timestamp": reopened.read_since(0, 1)[0].timestamp,
                "message": {"n": 1},
            },
            separators=(",", ":"),
        )
    ]


async def test_only_the_interrupted_tail_is_discarded(tmp_path: Path) -> None:
    """Loading streams the file, so the truncation offset has to survive many whole lines.

    The single-entry case above would still pass if recovery cut at a fixed or mis-accumulated
    offset; this one pins the offset to the exact end of the last complete line.
    """
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": index} for index in range(3)])
    durable = log.path.read_bytes()
    with log.path.open("ab") as handle:
        handle.write(b'{"seq":4,"run_id":"run-a","timestamp":"2026-01-01T00:00:00+00:00","mes')

    reopened = make_log(tmp_path)
    assert reopened.last_seq == 3
    assert reopened.path.read_bytes() == durable
    assert [record.seq for record in reopened.read_since(0, 10)] == [1, 2, 3]


async def test_appending_after_recovery_stays_contiguous(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": 1}])
    with log.path.open("ab") as handle:
        handle.write(b'{"seq":2,"run_id":"run-a"')

    reopened = make_log(tmp_path)
    assert await reopened.append("run-b", [{"n": 2}]) == 2
    assert [record.seq for record in reopened.read_since(0, 10)] == [1, 2]


def test_a_gap_in_the_sequence_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "channel.jsonl"
    path.write_text(
        '{"seq":1,"run_id":"a","timestamp":"t","message":{}}\n{"seq":3,"run_id":"a","timestamp":"t","message":{}}\n'
    )

    with pytest.raises(AppendLogError, match="not contiguous"):
        AppendLog(path, payload_key="message")


@pytest.mark.parametrize(
    "line",
    [
        "not json",
        "[1, 2]",
        '{"seq":1,"run_id":"a","timestamp":"t"}',
        '{"seq":1,"run_id":"a","timestamp":"t","message":{},"extra":1}',
        '{"seq":0,"run_id":"a","timestamp":"t","message":{}}',
        '{"seq":1,"run_id":"","timestamp":"t","message":{}}',
    ],
)
def test_a_malformed_entry_is_rejected(tmp_path: Path, line: str) -> None:
    path = tmp_path / "channel.jsonl"
    path.write_text(f"{line}\n")

    with pytest.raises(AppendLogError):
        AppendLog(path, payload_key="message")


def test_a_payload_key_cannot_shadow_a_record_field(tmp_path: Path) -> None:
    with pytest.raises(AppendLogError, match="shadow"):
        AppendLog(tmp_path / "channel.jsonl", payload_key="seq")


@pytest.mark.parametrize(("since", "limit"), [(-1, 10), (0, 0), (0, -1)])
def test_read_since_rejects_an_invalid_cursor(tmp_path: Path, since: int, limit: int) -> None:
    with pytest.raises(AppendLogError):
        make_log(tmp_path).read_since(since, limit)


# --- Reading by byte offset --------------------------------------------------------------


async def test_read_from_walks_the_channel_without_rereading_it(tmp_path: Path) -> None:
    """Each page resumes exactly where the last one stopped, which is the point of the offset."""
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": index} for index in range(5)])

    first = log.read_from(0, 2)
    second = log.read_from(first.next_offset, 2)
    third = log.read_from(second.next_offset, 2)

    assert [record.seq for record in first.records] == [1, 2]
    assert [record.seq for record in second.records] == [3, 4]
    assert [record.seq for record in third.records] == [5]
    assert third.next_offset == log.path.stat().st_size
    # Draining to the end and asking again yields nothing rather than starting over.
    assert log.read_from(third.next_offset, 2).records == []


def test_read_from_an_absent_file_yields_nothing(tmp_path: Path) -> None:
    page = make_log(tmp_path).read_from(0, 10)

    assert page.records == []
    assert page.next_offset == 0


async def test_read_from_stops_before_an_append_still_in_flight(tmp_path: Path) -> None:
    """A reader racing an append must stop on the last whole line, not parse half of one."""
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": 1}])
    whole = log.path.stat().st_size
    with log.path.open("ab") as handle:
        handle.write(b'{"seq":2,"run_id":"run-a","timestamp":"t","mes')

    page = log.read_from(0, 10)

    assert [record.seq for record in page.records] == [1]
    # Resuming from here picks the entry up once its remaining bytes land.
    assert page.next_offset == whole


async def test_offset_after_turns_a_sequence_cursor_back_into_an_offset(tmp_path: Path) -> None:
    """How a replicator resumes: it stores only a seq, and recovers the offset once per process."""
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": index} for index in range(4)])

    resumed = log.read_from(log.offset_after(2), 10)

    assert [record.seq for record in resumed.records] == [3, 4]
    assert log.offset_after(0) == 0
    assert log.offset_after(4) == log.path.stat().st_size
    # Past the end rather than an error: a control plane that reports more than this file holds
    # is a rewind case for the caller, not a corrupt read.
    assert log.offset_after(99) == log.path.stat().st_size


@pytest.mark.parametrize(("offset", "limit"), [(-1, 10), (0, 0), (0, -1)])
def test_read_from_rejects_an_invalid_page(tmp_path: Path, offset: int, limit: int) -> None:
    with pytest.raises(AppendLogError):
        make_log(tmp_path).read_from(offset, limit)


# --- Continuing another Runtime's numbering ------------------------------------------------


async def test_a_based_channel_numbers_its_first_entry_after_the_base(tmp_path: Path) -> None:
    """The cold-start case: a fresh file continuing a history that already reached seq 40."""
    log = AppendLog(tmp_path / "channel.jsonl", payload_key="message", base_seq=40)
    assert log.last_seq == 40
    assert log.is_empty

    assert await log.append("run-a", [{"n": 1}, {"n": 2}]) == 42

    assert [record.seq for record in log.read_since(0, 10)] == [41, 42]
    assert not log.is_empty


async def test_a_based_channel_reopens_with_the_same_base(tmp_path: Path) -> None:
    """Contiguity is checked from the base, so reloading must be told the base again."""
    log = AppendLog(tmp_path / "channel.jsonl", payload_key="message", base_seq=40)
    await log.append("run-a", [{"n": 1}])

    reopened = AppendLog(tmp_path / "channel.jsonl", payload_key="message", base_seq=40)

    assert reopened.last_seq == 41
    assert await reopened.append("run-b", [{"n": 2}]) == 42
    # The base is subtracted before counting lines, so seeking past seq 41 lands on the second
    # entry rather than running off the end of a two-line file.
    assert [record.seq for record in reopened.read_from(reopened.offset_after(41), 10).records] == [42]


def test_reopening_a_based_channel_with_the_wrong_base_is_rejected(tmp_path: Path) -> None:
    """Rather than silently reading a history whose numbering does not line up."""
    path = tmp_path / "channel.jsonl"
    path.write_text('{"seq":41,"run_id":"a","timestamp":"t","message":{}}\n')

    with pytest.raises(AppendLogError, match="not contiguous"):
        AppendLog(path, payload_key="message", base_seq=0)


async def test_rebasing_an_untouched_channel_moves_its_numbering(tmp_path: Path) -> None:
    log = make_log(tmp_path)

    log.rebase(55)

    assert log.base_seq == 55
    assert log.last_seq == 55
    assert await log.append("run-a", [{"n": 1}]) == 56


async def test_rebasing_a_channel_that_holds_entries_is_refused(tmp_path: Path) -> None:
    """Renumbering entries that exist would describe a different history than the stored one."""
    log = make_log(tmp_path)
    await log.append("run-a", [{"n": 1}])

    with pytest.raises(AppendLogError, match="cannot be rebased"):
        log.rebase(55)


def test_a_negative_base_is_refused(tmp_path: Path) -> None:
    with pytest.raises(AppendLogError, match="non-negative"):
        AppendLog(tmp_path / "channel.jsonl", payload_key="message", base_seq=-1)


# --- Waking whoever replicates the channel -------------------------------------------------


async def test_a_durable_append_raises_the_change_signal(tmp_path: Path) -> None:
    signal = ChangeSignal()
    log = AppendLog(tmp_path / "channel.jsonl", payload_key="message", signal=signal)
    assert not signal.raised

    await log.append("run-a", [{"n": 1}])

    assert signal.raised


async def test_an_empty_append_raises_nothing(tmp_path: Path) -> None:
    """There is nothing to replicate, and a spurious wake-up costs a full drain pass."""
    signal = ChangeSignal()
    log = AppendLog(tmp_path / "channel.jsonl", payload_key="message", signal=signal)

    await log.append("run-a", [])

    assert not signal.raised
