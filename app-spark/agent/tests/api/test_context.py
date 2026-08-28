"""``GET/PUT /context``: exporting the trusted history, and seeding a cold Runtime with one.

The context is the only artifact a conversation can be resumed from, so both directions are
guarded: the export is tagged with the version it was taken at, and the import refuses anything
that would overwrite a Runtime already holding a conversation of its own.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelRequest, UserPromptPart

from app_spark_agent.state import STATE_SCHEMA_VERSION, ConversationContext
from tests.api.support import get_transcript_messages, run_in_flight, run_turn

# Deliberately not 0 or 1: a restored Runtime continues someone else's numbering, so a version
# the receiving Runtime could have reached on its own would hide an off-by-one.
COLD_VERSION = 7


def cold_context(conversation_id: str, *, context_version: int = COLD_VERSION) -> dict[str, Any]:
    """Build the context document a control plane would hand to a fresh Runtime."""
    context = ConversationContext(
        conversation_id=conversation_id,
        context_version=context_version,
        messages=[
            ModelRequest(
                parts=[UserPromptPart(content="earlier turn")],
                run_id=str(uuid4()),
                conversation_id=conversation_id,
            )
        ],
    )
    return context.as_payload()


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
