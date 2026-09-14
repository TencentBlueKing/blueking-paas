"""A whole coding session against a real process, for free.

This is :mod:`tests.e2e.test_coding_session` without the model bill: the same uvicorn process,
the same AG-UI stream, the same three durable channels -- only the model is scripted.

It earns its place next to the in-process tests by covering the one thing they structurally
cannot. The in-process tests hand a model object to ``create_runtime_app(agent=...)``; here the
Runtime is assembled by ``create_app_from_settings()`` from ``APP_SPARK_AGENT_*`` alone, which
is how every external control plane starts it. A fake that could only be injected in-process
would be useless to them.
"""

from __future__ import annotations

from pathlib import Path

from app_spark_agent.fake_model import NOTE_FILENAME_TEMPLATE, WRITE_FILE_TOOL
from tests.support import console
from tests.support.live import model_messages, part_kinds, stored_events
from tests.support.live_fixtures import StartRuntime

FIRST_NOTE = NOTE_FILENAME_TEMPLATE.format(turn=1)
SECOND_NOTE = NOTE_FILENAME_TEMPLATE.format(turn=2)


def test_a_fake_model_runs_a_real_session_without_an_api_key(
    start_runtime: StartRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    runtime = start_runtime(MODEL="fake:write-file")

    console.banner("turn 1: the scripted agent changes the workspace with the real tools")
    first = runtime.turn(conversation_id=conversation_id, prompt="write my first note")

    assert first.tool_calls == [WRITE_FILE_TOOL]
    assert "TOOL_CALL_RESULT" in first.event_types
    assert (workspace / FIRST_NOTE).read_text().strip().endswith("write my first note")
    assert FIRST_NOTE in first.reply

    console.banner("turn 2: the same process serves the next turn")
    second = runtime.turn(conversation_id=conversation_id, prompt="write my second note")

    # The fake reads its state out of the history it is handed, so a second turn on the same
    # process has to move on rather than repeat. Anything cached in the process would show up
    # here as a rewrite of the first note.
    assert (workspace / SECOND_NOTE).read_text().strip().endswith("write my second note")
    assert SECOND_NOTE in second.reply

    console.banner("what the Runtime kept")
    health = runtime.health()
    transcript = runtime.drain("log")
    ui_events = runtime.drain("ui-events")
    exported = runtime.context()

    assert health["conversation_id"] == conversation_id
    assert health["running"] is False
    assert health["log_seq"] == len(transcript) == transcript[-1]["seq"]
    assert health["ui_event_seq"] == len(ui_events) == ui_events[-1]["seq"]
    assert health["context_version"] == exported["context_version"] >= 2

    # A scripted model still has to produce a real conversation shape, or the control plane
    # would be reading a stream no live session ever looks like.
    assert {"user-prompt", "tool-call", "tool-return", "text"} <= part_kinds(model_messages(transcript))
    types = [str(event["type"]) for event in stored_events(ui_events)]
    assert types[0] == "RUN_STARTED"
    assert types[-1] == "RUN_FINISHED"
    assert types.count("TEXT_MESSAGE_START") == types.count("TEXT_MESSAGE_END")
