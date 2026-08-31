"""``GET /log``: the raw model transcript, and the cursor contract both drains share.

``/log`` and ``/ui-events`` are two channels served by one paging implementation, so the
cursor rules are pinned once here, against both endpoints, rather than twice in two files.
What the AG-UI channel stores is its own question and lives in
:mod:`tests.api.test_ui_events`.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app_spark_agent import settings
from tests.api.support import ApiFactory, drain_channel, run_turn
from tests.support.fake_models import probe, tool_calling_model

CHANNELS = ["/log", "/ui-events"]


def test_a_turn_records_the_user_request_and_the_model_reply(api: TestClient) -> None:
    conversation_id = str(uuid4())

    run_turn(api, conversation_id=conversation_id, prompt="the question")

    page: dict[str, Any] = api.get("/log").json()
    records: list[dict[str, Any]] = page["records"]
    assert page["since"] == 0
    assert page["last_seq"] == 2
    assert [record["seq"] for record in records] == [1, 2]
    assert [record["message"]["kind"] for record in records] == ["request", "response"]
    # Every entry is attributable to the run that produced it, which is what replay detection
    # is later asked about.
    assert len({record["run_id"] for record in records}) == 1


def test_a_tool_round_is_recorded_message_by_message(make_api: ApiFactory) -> None:
    """The transcript is the conversation itself, tool traffic included -- not just its ends."""
    api = make_api(model=tool_calling_model(1), tools=[probe])

    run_turn(api, conversation_id=str(uuid4()))

    records = drain_channel(api, "/log")
    part_kinds = {part["part_kind"] for record in records for part in record["message"]["parts"]}
    assert [record["message"]["kind"] for record in records] == [
        "request",
        "response",
        "request",
        "response",
    ]
    assert {"user-prompt", "tool-call", "tool-return", "text"} <= part_kinds


@pytest.mark.parametrize("channel", CHANNELS)
def test_a_drain_resumes_from_its_cursor(api: TestClient, channel: str) -> None:
    run_turn(api, conversation_id=str(uuid4()))

    whole: dict[str, Any] = api.get(channel).json()
    records: list[dict[str, Any]] = whole["records"]
    assert records, f"the run wrote nothing to {channel}"

    first: dict[str, Any] = api.get(channel, params={"since": 0, "limit": 1}).json()
    rest: dict[str, Any] = api.get(channel, params={"since": 1}).json()

    assert [record["seq"] for record in first["records"]] == [1]
    assert rest["records"] == records[1:]
    # Paging one record at a time must reach the same place as asking for everything at once.
    assert drain_channel(api, channel, limit=1) == records


@pytest.mark.parametrize("channel", CHANNELS)
def test_an_exhausted_drain_reports_the_cursor_to_resume_from(
    api: TestClient,
    channel: str,
) -> None:
    """A caught-up client is told nothing changed, not that the channel is empty."""
    run_turn(api, conversation_id=str(uuid4()))
    last_seq: int = api.get(channel).json()["last_seq"]

    drained: dict[str, Any] = api.get(channel, params={"since": last_seq}).json()

    assert drained["records"] == []
    assert drained["since"] == last_seq
    assert drained["last_seq"] == last_seq


@pytest.mark.parametrize("channel", CHANNELS)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"since": -1}, id="negative-cursor"),
        pytest.param({"limit": 0}, id="empty-page"),
        pytest.param({"limit": settings.MAX_DRAIN_LIMIT + 1}, id="oversized-page"),
        pytest.param({"since": "soon"}, id="cursor-is-not-a-number"),
    ],
)
def test_an_invalid_cursor_is_rejected(
    api: TestClient,
    channel: str,
    params: dict[str, Any],
) -> None:
    assert api.get(channel, params=params).status_code == 422
