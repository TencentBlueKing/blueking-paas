"""``GET /ui-events``: the stored, replayable copy of what the client saw."""

import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, cast
from uuid import uuid4

import pytest
from ag_ui.core import BaseEvent
from fastapi.testclient import TestClient

from app_spark_agent.server import routes
from app_spark_agent.state import AppendLog
from tests.api.support import ApiFactory, drain_channel, run_turn
from tests.support.fake_models import probe, tool_calling_model


def stored_events(api: TestClient) -> list[dict[str, Any]]:
    """Return the AG-UI events the Runtime kept, in replay order."""
    return [record["event"] for record in drain_channel(api, "/ui-events")]


def deltas(events: list[dict[str, Any]], event_type: str) -> list[str]:
    """Return the delta of every event of one type."""
    return [event["delta"] for event in events if event["type"] == event_type]


def test_streamed_deltas_are_stored_as_one_assembled_message(api: TestClient) -> None:
    """Per-token deltas stay on the wire; the log keeps one content event per message."""
    outcome = run_turn(api, conversation_id=str(uuid4()))

    streamed = deltas(outcome.events, "TEXT_MESSAGE_CONTENT")
    stored = stored_events(api)

    assert len(streamed) > 1, "the model must actually stream for this test to mean anything"
    assert "".join(streamed) == "hello"
    assert deltas(stored, "TEXT_MESSAGE_CONTENT") == ["hello"]


def test_the_stored_stream_stays_a_valid_ag_ui_sequence(make_api: ApiFactory) -> None:
    """Coalescing must not lose the framing: every message it stores is opened and closed."""
    api = make_api(model=tool_calling_model(1), tools=[probe])

    run_turn(api, conversation_id=str(uuid4()))

    stored = stored_events(api)
    types = [event["type"] for event in stored]
    assert types[0] == "RUN_STARTED"
    assert types[-1] == "RUN_FINISHED"
    assert types.count("TEXT_MESSAGE_START") == types.count("TEXT_MESSAGE_END") == 1
    assert types.count("TOOL_CALL_START") == types.count("TOOL_CALL_END") == 1


def test_tool_calls_are_stored_with_their_arguments(make_api: ApiFactory) -> None:
    """A replayed UI has to show what the agent did, not just that it said something."""
    api = make_api(model=tool_calling_model(1), tools=[probe])

    outcome = run_turn(api, conversation_id=str(uuid4()))

    assert "TOOL_CALL_RESULT" in outcome.event_types
    stored = stored_events(api)
    assert "TOOL_CALL_RESULT" in [event["type"] for event in stored]
    assert json.loads("".join(deltas(stored, "TOOL_CALL_ARGS"))) == {"index": 0}


def test_a_run_whose_stream_breaks_still_ends_in_the_stored_log(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The error a broken stream ends with is stored too: a client that reconnected replays the
    log, not the stream it missed, and must see the run end."""
    recording = routes.record_ui_events

    async def breaking(stream: AsyncIterator[BaseEvent], *, log: AppendLog, run_id: str) -> AsyncIterator[BaseEvent]:
        recorded = cast(AsyncGenerator[BaseEvent], recording(stream, log=log, run_id=run_id))
        try:
            yield await anext(recorded)
            # The recorder stores an event once the next one is asked for; break only after that.
            await anext(recorded)
            raise RuntimeError("the stream broke")
        finally:
            await recorded.aclose()

    monkeypatch.setattr(routes, "record_ui_events", breaking)

    outcome = run_turn(api, conversation_id=str(uuid4()))

    assert outcome.event_types[-1] == "RUN_ERROR"
    stored = stored_events(api)
    assert [event["type"] for event in stored] == ["RUN_STARTED", "RUN_ERROR"]
    assert "the stream broke" in stored[-1]["message"]
