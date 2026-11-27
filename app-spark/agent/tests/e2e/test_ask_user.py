"""Live E2E tests for `AskUser(answerer=None)` against the real configured LLM.

These tests verify two things mocks cannot prove:
1. Under the production system prompt, an underspecified product request actually causes the model
   to call `ask_user_question` with structured options and pause cleanly, then resume once answers
   are submitted.
2. When the user ignores the pending question card and sends a direct chat message instead, the
   real LLM provider accepts the auto-closed `assistant(tool_calls) -> tool -> user` history and
   acts on the new message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai_harness.ask_user import TOOL_NAME

from app_spark_agent.cap.ask_user import BYPASSED_BY_USER_MESSAGE
from tests.support import console
from tests.support.live import LiveRuntime, model_messages, part_kinds

pytestmark = pytest.mark.live

AMBIGUOUS_APP_REQUEST = "我想做一个团队内部的小应用来管理日常事务，但具体做什么方向、面向什么使用场景和需要哪些核心功能都还没想好，帮我做一个。"
BYPASS_DIRECT_REQUEST = "先不用问了，需求改一下：请只在工作区根目录创建一个 hello.txt 文件，内容为 OK，然后回复 DONE。"


def _pause_with_question(runtime: LiveRuntime, conversation_id: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Send an underspecified request and verify it pauses with structured pending questions."""
    paused = runtime.turn(conversation_id=conversation_id, prompt=AMBIGUOUS_APP_REQUEST)

    assert TOOL_NAME in paused.tool_calls, (
        f"expected the model to call {TOOL_NAME!r}, got tool_calls={paused.tool_calls!r}, reply={paused.reply!r}"
    )
    finished = paused.events[-1]
    assert finished["type"] == "RUN_FINISHED"
    pending_ids: list[str] = finished.get("outcome", {}).get("pendingToolCallIds") or []
    assert pending_ids, f"expected pendingToolCallIds on RUN_FINISHED, got {finished!r}"

    health_paused = runtime.health()
    pending_questions: list[dict[str, Any]] = health_paused["pending_questions"]
    console.note(f"pending_questions={json.dumps(pending_questions, ensure_ascii=False)}")
    assert health_paused["running"] is False
    assert [item["tool_call_id"] for item in pending_questions] == pending_ids
    return pending_ids, pending_questions


def _pick_first_option_responses(pending_questions: list[dict[str, Any]]) -> list[dict[str, object]]:
    """Select the first (recommended) option for every pending question."""
    responses: list[dict[str, object]] = []
    for call in pending_questions:
        answers: list[dict[str, object]] = [
            {
                "header": question["header"],
                "selected": [question["options"][0]["label"]],
            }
            for question in call["questions"]
        ]
        responses.append({"toolCallId": call["tool_call_id"], "answers": answers})
    return responses


def test_ask_user_triggers_on_ambiguous_request_and_resumes_with_answers(
    runtime: LiveRuntime,
    conversation_id: str,
) -> None:
    console.banner("turn 1: underspecified request triggers ask_user_question and pauses cleanly")
    pending_ids, pending_questions = _pause_with_question(runtime, conversation_id)
    for item in pending_questions:
        assert item["questions"]
        for question in item["questions"]:
            assert question["header"]
            assert question["question"]
            assert len(question["options"]) >= 2

    console.banner("turn 2: submit selected answers and verify the model resumes cleanly")
    responses = _pick_first_option_responses(pending_questions)
    resumed = runtime.answer(conversation_id=conversation_id, responses=responses)

    tool_results = [event for event in resumed.events if event.get("type") == "TOOL_CALL_RESULT"]
    assert any(event.get("toolCallId") in pending_ids for event in tool_results)
    assert resumed.events[-1]["type"] == "RUN_FINISHED"
    assert resumed.reply.strip() or resumed.tool_calls

    health_resumed = runtime.health()
    transcript = runtime.drain("log")
    ui_events = runtime.drain("ui-events")
    assert health_resumed["running"] is False
    assert health_resumed["log_seq"] == len(transcript) == transcript[-1]["seq"]
    assert health_resumed["ui_event_seq"] == len(ui_events) == ui_events[-1]["seq"]
    assert {"user-prompt", "tool-call", "tool-return"} <= part_kinds(model_messages(transcript))


def test_ask_user_can_be_bypassed_by_a_direct_chat_message(
    runtime: LiveRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    console.banner("turn 1: trigger ask_user_question pause")
    pending_ids, _ = _pause_with_question(runtime, conversation_id)

    console.banner("turn 2: ignore question card and send a direct chat message")
    bypassed = runtime.turn(conversation_id=conversation_id, prompt=BYPASS_DIRECT_REQUEST)

    assert bypassed.event_types[0] == "RUN_STARTED"
    assert bypassed.event_types[1] == "TOOL_CALL_RESULT"
    assert bypassed.events[1]["toolCallId"] in set(pending_ids)
    assert bypassed.events[1]["content"] == BYPASSED_BY_USER_MESSAGE
    assert bypassed.events[-1]["type"] == "RUN_FINISHED"
    assert "DONE" in bypassed.reply.upper()
    assert (workspace / "hello.txt").read_text().strip() == "OK"

    health_after = runtime.health()
    assert health_after["running"] is False
    assert health_after["pending_questions"] == []
