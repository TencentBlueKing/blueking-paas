"""Pure AG-UI request and event helpers shared by in-process and live tests."""

import json
from collections.abc import Sequence
from typing import Any, cast
from uuid import uuid4

# What a client asks for when it wants the AG-UI event stream rather than a buffered body.
SSE_HEADERS = {"Accept": "text/event-stream"}


def run_body(
    *,
    conversation_id: str,
    run_id: str,
    context_version: int,
    prompt: str = "hello",
) -> dict[str, object]:
    """Build a minimal valid AG-UI run request.

    This document is AG-UI's, so it keeps AG-UI's camelCase -- including ``threadId``, which is
    the protocol's name for what the Runtime calls a conversation everywhere else. Only what the
    Runtime itself emits is snake_case.
    """
    return {
        "threadId": conversation_id,
        "runId": run_id,
        "state": {},
        "messages": [{"id": str(uuid4()), "role": "user", "content": prompt}],
        "tools": [],
        "context": [],
        "forwardedProps": {"contextVersion": context_version},
    }


def sse_events(body: str) -> list[dict[str, Any]]:
    """Parse an SSE response body into the JSON events it carried.

    Shared by the in-process route tests and the live subprocess tests, which assert on the same
    AG-UI event stream and only differ in how they got hold of the body.
    """
    events: list[dict[str, Any]] = []
    for frame in body.replace("\r\n", "\n").split("\n\n"):
        data = "\n".join(
            line.removeprefix("data:").lstrip() for line in frame.splitlines() if line.startswith("data:")
        )
        if data:
            events.append(cast(dict[str, Any], json.loads(data)))
    return events


def assistant_text(events: Sequence[dict[str, Any]]) -> str:
    """Return the assistant's streamed message, reassembled from its text deltas."""
    return "".join(
        event["delta"]
        for event in events
        if event.get("type") == "TEXT_MESSAGE_CONTENT" and isinstance(event.get("delta"), str)
    )
