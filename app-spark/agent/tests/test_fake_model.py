"""The fake model's contract, which the control plane's integration tests depend on."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel
from pytest import MonkeyPatch

from app_spark_agent import settings
from app_spark_agent.agent import build_model
from app_spark_agent.fake_model import (
    NOTE_FILENAME_TEMPLATE,
    WRITE_FILE_TOOL,
    TextStep,
    ToolCallStep,
    UnknownFakeScenarioError,
    build_fake_model,
    plan_step,
)
from app_spark_agent.server import create_runtime_app
from tests.api.support import RUNTIME_TOKEN, AuthedTestClient, run_turn


def user_turn(prompt: str) -> ModelRequest:
    """One user message, as the model receives it."""
    return ModelRequest(parts=[UserPromptPart(content=prompt)])


def wrote_file(filename: str) -> tuple[ModelResponse, ModelRequest]:
    """The call-and-result pair a completed ``write_file`` leaves in the history."""
    call = ModelResponse(parts=[ToolCallPart(tool_name=WRITE_FILE_TOOL, args={"path": filename}, tool_call_id="c1")])
    result = ModelRequest(parts=[ToolReturnPart(tool_name=WRITE_FILE_TOOL, content="ok", tool_call_id="c1")])
    return call, result


def test_write_file_scenario_calls_the_tool_before_answering() -> None:
    step = plan_step("write-file", [user_turn("build me a page")])

    assert isinstance(step, ToolCallStep)
    assert step.tool_name == WRITE_FILE_TOOL
    assert step.args["path"] == NOTE_FILENAME_TEMPLATE.format(turn=1)
    # The prompt is echoed into the file so a caller can assert the write really carried
    # this turn's request rather than a fixed blob.
    assert "build me a page" in cast(str, step.args["content"])


def test_write_file_scenario_answers_once_the_tool_has_returned() -> None:
    messages: list[ModelMessage] = [user_turn("build me a page"), *wrote_file("note.md")]

    step = plan_step("write-file", messages)

    assert isinstance(step, TextStep)
    assert NOTE_FILENAME_TEMPLATE.format(turn=1) in "".join(step.chunks)


def test_a_second_turn_writes_again_despite_the_first_turn_still_being_in_history() -> None:
    """State is read from the history, so a stale tool result must not suppress a new write.

    Keying off the whole history rather than the part after the last user message is the
    obvious mistake here, and it makes every turn after the first silently skip its write.
    """
    messages: list[ModelMessage] = [
        user_turn("first"),
        *wrote_file(NOTE_FILENAME_TEMPLATE.format(turn=1)),
        ModelResponse(parts=[TextPart(content="done")]),
        user_turn("second"),
    ]

    step = plan_step("write-file", messages)

    assert isinstance(step, ToolCallStep)
    assert step.args["path"] == NOTE_FILENAME_TEMPLATE.format(turn=2)
    assert "second" in cast(str, step.args["content"])


def test_chat_scenario_streams_text_in_more_than_one_chunk() -> None:
    step = plan_step("chat", [user_turn("hello there")])

    assert isinstance(step, TextStep)
    assert len(step.chunks) > 1
    assert "hello there" in "".join(step.chunks)
    assert step.pause_after is None


def test_slow_scenario_pauses_after_the_stream_has_started() -> None:
    """The pause must come after a chunk, not before it.

    Its whole purpose is to let a caller observe a run in flight; pausing before the first
    chunk would leave the caller unable to tell "started and waiting" from "not started".
    """
    step = plan_step("slow", [user_turn("hello")])

    assert isinstance(step, TextStep)
    assert step.pause_after == 0
    assert len(step.chunks) > 1


def test_an_unknown_scenario_is_refused_by_name() -> None:
    with pytest.raises(UnknownFakeScenarioError) as exc_info:
        build_fake_model("does-not-exist")

    assert "does-not-exist" in str(exc_info.value)
    assert "write-file" in str(exc_info.value)


def test_a_fake_model_name_never_reaches_the_provider_machinery(monkeypatch: MonkeyPatch) -> None:
    """``infer_model`` rejects unknown providers, so ``fake:`` has to be intercepted first."""
    monkeypatch.setattr(settings, "MODEL", "fake:chat")

    model = build_model()

    assert isinstance(model, FunctionModel)
    assert model.model_name == "fake:chat"


def test_a_fake_runtime_writes_a_real_file_and_reports_it(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """The whole point of the fake: a Runtime built from settings alone, with no API key.

    This exercises the real agent -- real workspace tools, real AG-UI event stream -- and only
    swaps out the model, which is exactly what the control plane's tests rely on.
    """
    monkeypatch.setattr(settings, "MODEL", "fake:write-file")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", RUNTIME_TOKEN)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    app = create_runtime_app(workspace=workspace, state_dir=tmp_path / "state")
    with AuthedTestClient(app) as client:
        conversation_id = str(uuid4())
        first = run_turn(client, conversation_id=conversation_id, prompt="write my note")
        second = run_turn(client, conversation_id=conversation_id, prompt="and another")

        health: dict[str, Any] = client.get("/health").json()

    assert "TOOL_CALL_START" in first.event_types
    assert "TEXT_MESSAGE_CONTENT" in first.event_types

    note = workspace / NOTE_FILENAME_TEMPLATE.format(turn=1)
    assert note.exists()
    assert "write my note" in note.read_text()
    assert NOTE_FILENAME_TEMPLATE.format(turn=1) in first.reply

    # A second turn proves the fake reads its state from the history: a process serves many
    # turns, and anything cached outside the messages would make this one repeat the first.
    later_note = workspace / NOTE_FILENAME_TEMPLATE.format(turn=2)
    assert later_note.exists()
    assert "and another" in later_note.read_text()
    assert NOTE_FILENAME_TEMPLATE.format(turn=2) in second.reply

    assert health["running"] is False
    assert health["log_seq"] > 0
    assert health["ui_event_seq"] > 0
