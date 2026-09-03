"""Append-only channel behavior: contiguity, cursors, and crash recovery."""

import json
from pathlib import Path

import pytest

from app_spark_agent.state import AppendLog, AppendLogError


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
