"""``GET /health``: the single call a control plane polls the Runtime with.

Everything it reports is a cursor into something a client can fetch in full elsewhere, so the
interesting assertion is not the shape of the document but that its numbers agree with the
endpoints they point at.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app_spark_agent import settings
from tests.api.support import drain_channel, run_turn


def test_an_empty_runtime_reports_no_conversation(api: TestClient) -> None:
    reported: dict[str, Any] = api.get("/health").json()

    assert reported["status"] == "ok"
    assert reported["model"] == settings.MODEL
    assert reported["conversation_id"] is None
    assert reported["context_version"] == 0
    assert reported["log_seq"] == 0
    assert reported["ui_event_seq"] == 0
    assert reported["running"] is False


def test_every_reported_cursor_matches_the_endpoint_it_points_at(api: TestClient) -> None:
    conversation_id = str(uuid4())

    run_turn(api, conversation_id=conversation_id)

    reported: dict[str, Any] = api.get("/health").json()
    transcript = drain_channel(api, "/log")
    events = drain_channel(api, "/ui-events")
    context: dict[str, Any] = api.get("/context").json()

    assert reported["conversation_id"] == conversation_id
    assert reported["context_version"] == context["context_version"]
    assert reported["log_seq"] == transcript[-1]["seq"] == len(transcript)
    assert reported["ui_event_seq"] == events[-1]["seq"] == len(events)
    assert reported["running"] is False
