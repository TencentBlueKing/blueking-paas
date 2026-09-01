"""``GET/PUT /context``: exporting the trusted history, and seeding a cold Runtime with one.

The context is the only artifact a conversation can be resumed from, so both directions are
guarded: the export is tagged with the version it was taken at, and the import refuses anything
that would overwrite a Runtime already holding a conversation of its own.
"""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app_spark_agent.state import STATE_SCHEMA_VERSION, ConversationContext
from tests.api.support import (
    COLD_VERSION,
    cold_context,
    drain_channel,
    get_transcript_messages,
    run_in_flight,
    run_turn,
)


def test_an_empty_conversation_serves_an_empty_context(api: TestClient) -> None:
    response = api.get("/context")

    assert response.json() == ConversationContext().as_payload()
    assert response.headers["etag"] == "0"


def test_the_export_is_tagged_with_the_version_it_was_taken_at(api: TestClient) -> None:
    conversation_id = str(uuid4())

    run_turn(api, conversation_id=conversation_id)

    response = api.get("/context")
    exported: dict[str, Any] = response.json()
    assert exported["schema_version"] == STATE_SCHEMA_VERSION
    assert exported["conversation_id"] == conversation_id
    assert response.headers["etag"] == str(exported["context_version"])


def test_a_cold_context_is_restored_verbatim(api: TestClient) -> None:
    payload = cold_context(str(uuid4()))

    restored = api.put("/context", json=payload)

    assert restored.status_code == 200, restored.text
    assert restored.json() == payload
    assert restored.headers["etag"] == str(COLD_VERSION)
    assert api.get("/context").json() == payload


def test_restoring_the_same_context_twice_is_accepted(api: TestClient) -> None:
    """A retried transfer must not look like an attempt to overwrite the conversation."""
    payload = cold_context(str(uuid4()))

    assert api.put("/context", json=payload).status_code == 200
    assert api.put("/context", json=payload).status_code == 200


def test_a_different_context_cannot_overwrite_an_active_one(api: TestClient) -> None:
    assert api.put("/context", json=cold_context(str(uuid4()))).status_code == 200

    refused = api.put("/context", json=cold_context(str(uuid4())))

    assert refused.status_code == 409
    assert "cannot be overwritten" in refused.json()["detail"]


def test_if_match_rejects_a_stale_version(api: TestClient) -> None:
    payload = cold_context(str(uuid4()))

    stale = api.put("/context", json=payload, headers={"If-Match": "3"})

    assert stale.status_code == 412
    assert "Runtime is at 0" in stale.json()["detail"]
    assert api.put("/context", json=payload, headers={"If-Match": "0"}).status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"schema_version": STATE_SCHEMA_VERSION - 1}, id="unreadable-schema"),
        pytest.param(
            {
                "schema_version": STATE_SCHEMA_VERSION,
                "conversation_id": None,
                "context_version": 1,
                "messages": [{"nonsense": True}],
            },
            id="unparseable-message",
        ),
        pytest.param(
            {
                "schema_version": STATE_SCHEMA_VERSION,
                "conversation_id": "conv-1",
                "context_version": -1,
                "messages": [],
            },
            id="negative-version",
        ),
    ],
)
def test_an_invalid_cold_context_is_rejected(api: TestClient, payload: dict[str, Any]) -> None:
    assert api.put("/context", json=payload).status_code == 422
    assert api.get("/context").json()["context_version"] == 0


def test_a_body_that_is_not_json_is_rejected(api: TestClient) -> None:
    response = api.put("/context", content=b"{")

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON context payload."


def test_a_run_resumes_a_restored_context(api: TestClient) -> None:
    """The transfer moves the context, not the history: the cold turns are not replayed."""
    conversation_id = str(uuid4())
    payload = cold_context(conversation_id)
    assert api.put("/context", json=payload).status_code == 200

    run_turn(api, conversation_id=conversation_id)

    context: dict[str, Any] = api.get("/context").json()
    assert context["context_version"] == COLD_VERSION + 1
    assert context["messages"][0]["parts"][0]["content"] == "earlier turn"
    assert len(get_transcript_messages(api)) == 2, "this Runtime only logs what it observed itself"


# --- Seeding the numbering the restored conversation continues from ------------------------


def test_a_restored_runtime_continues_the_conversation_numbering(api: TestClient) -> None:
    """Without this, a replacement Runtime writes an entry 1 the control plane already has."""
    conversation_id = str(uuid4())
    payload = cold_context(conversation_id)
    seeded = api.put("/context", params={"log_seq": 40, "ui_event_seq": 55}, json=payload)
    assert seeded.status_code == 200, seeded.text

    run_turn(api, conversation_id=conversation_id)

    assert next(record["seq"] for record in drain_channel(api, "/log")) == 41
    assert next(record["seq"] for record in drain_channel(api, "/ui-events")) == 56


def test_the_cursors_ride_outside_the_body(api: TestClient) -> None:
    """The body has to stay byte-for-byte what ``GET /context`` produced, so it holds neither."""
    payload = cold_context()

    restored = api.put("/context", params={"log_seq": 40, "ui_event_seq": 55}, json=payload)

    assert restored.json() == payload
    assert api.get("/context").json() == payload


def test_a_restore_without_cursors_starts_the_numbering_at_one(api: TestClient) -> None:
    """Omitting them means "this conversation has no history elsewhere", not "unknown"."""
    conversation_id = str(uuid4())
    assert api.put("/context", json=cold_context(conversation_id)).status_code == 200

    run_turn(api, conversation_id=conversation_id)

    assert next(record["seq"] for record in drain_channel(api, "/log")) == 1


def test_a_runtime_that_already_wrote_history_refuses_to_be_renumbered(api: TestClient) -> None:
    """Renumbering existing entries would describe a history the control plane does not have."""
    conversation_id = str(uuid4())
    run_turn(api, conversation_id=conversation_id)
    seqs_before = [record["seq"] for record in drain_channel(api, "/log")]

    # A fresh Runtime is the only thing a cold context may be injected into, and this one has
    # both a conversation of its own and entries in its channels.
    refused = api.put("/context", params={"log_seq": 40}, json=cold_context())

    assert refused.status_code == 409
    assert [record["seq"] for record in drain_channel(api, "/log")] == seqs_before


@pytest.mark.parametrize("params", [{"log_seq": -1}, {"ui_event_seq": -1}])
def test_a_negative_cursor_is_rejected(api: TestClient, params: dict[str, int]) -> None:
    assert api.put("/context", params=params, json=cold_context()).status_code == 422
    assert api.get("/context").json()["context_version"] == 0


async def test_a_restore_is_refused_while_a_run_is_in_flight(tmp_path: Path) -> None:
    """Both mutating endpoints share one guard, so neither can start while the other holds it."""
    async with run_in_flight(tmp_path) as held:
        refused = await held.client.put("/context", json=cold_context(held.conversation_id))

        assert refused.status_code == 409
        assert "already in progress" in refused.json()["detail"]

        await held.release()
        # Refused, not queued: the restore left no trace once the run handed the guard back.
        exported: dict[str, Any] = (await held.client.get("/context")).json()
        assert exported["context_version"] == 1
