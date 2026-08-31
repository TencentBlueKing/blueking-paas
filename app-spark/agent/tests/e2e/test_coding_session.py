"""A plain coding session: two turns, and everything the Runtime kept about them.

This is the scenario the other two live files assume already works. The first turn has to reach
for real tools and actually change the workspace, the second has to answer from the history the
Runtime holds rather than from anything the client resent, and afterwards the three durable
channels have to agree with the cursors ``/health`` reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e import console
from tests.e2e.live import LiveRuntime, model_messages, part_kinds, stored_events

pytestmark = pytest.mark.live

HEADING = "<h1>Hello World</h1>"
CREATE = f"Create only index.html containing exactly {HEADING}. Reply DONE."
RECALL = "Without using tools, reply only with the filename you created."


def test_a_coding_session_is_streamed_applied_and_recorded(
    runtime: LiveRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    console.banner("turn 1: the agent changes the workspace with its own tools")
    first = runtime.turn(conversation_id=conversation_id, prompt=CREATE)

    assert first.tool_calls, "the model answered without ever touching the workspace"
    assert "TOOL_CALL_RESULT" in first.event_types
    # The stream is AG-UI and nothing else, so a client can forward it to a browser untouched;
    # the model history travels over `/log` instead.
    assert "CUSTOM" not in first.event_types
    assert "DONE" in first.reply.upper()
    assert (workspace / "index.html").read_text().strip() == HEADING

    console.banner("turn 2: the agent answers from the Runtime's own history")
    second = runtime.turn(conversation_id=conversation_id, prompt=RECALL)

    assert "index.html" in second.reply.lower()

    console.banner("what the Runtime kept")
    health = runtime.health()
    transcript = runtime.drain("log")
    ui_events = runtime.drain("ui-events")
    exported = runtime.context()

    assert health["conversation_id"] == conversation_id
    assert health["log_seq"] == len(transcript) == transcript[-1]["seq"]
    assert health["ui_event_seq"] == len(ui_events) == ui_events[-1]["seq"]
    assert health["context_version"] == exported["context_version"] >= 2

    # The transcript is the conversation itself, tool traffic included; the context is only
    # what the model was last given. The two are allowed to differ, and usually do.
    assert len(transcript) >= len(exported["messages"])
    assert {"user-prompt", "tool-call", "tool-return", "text"} <= part_kinds(
        model_messages(transcript)
    )

    # Stored UI events are a replayable stream, with the per-token deltas already coalesced.
    types = [str(event["type"]) for event in stored_events(ui_events)]
    assert types[0] == "RUN_STARTED"
    assert types[-1] == "RUN_FINISHED"
    assert types.count("TEXT_MESSAGE_START") == types.count("TEXT_MESSAGE_END")
