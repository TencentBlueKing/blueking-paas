"""Core behavioral tests for :class:`app_spark_agent.cap.ask_user.PendingAskUser`."""

from __future__ import annotations

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai_harness.ask_user import DECLINED, TOOL_NAME

from app_spark_agent.cap.ask_user import PendingAskUser


def make_ask_call(tool_call_id: str = "call-ask-1") -> ToolCallPart:
    return ToolCallPart(
        tool_name=TOOL_NAME,
        args={
            "questions": [
                {
                    "header": "Theme",
                    "question": "Which theme should the app use?",
                    "options": [
                        {"label": "Light (Recommended)", "description": "Bright and clean"},
                        {"label": "Dark"},
                    ],
                }
            ]
        },
        tool_call_id=tool_call_id,
    )


def test_pending_tracks_only_unanswered_calls_in_the_final_response() -> None:
    earlier = make_ask_call("call-old")
    current = make_ask_call("call-current")
    sibling = ToolCallPart(tool_name="read_file", args={"path": "main.py"}, tool_call_id="call-read")

    # Empty or completed history has no pending questions.
    assert PendingAskUser([]).tool_calls() == []
    completed: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart("first")]),
        ModelResponse(parts=[earlier]),
        ModelRequest(parts=[ToolReturnPart(tool_name=TOOL_NAME, content=DECLINED, tool_call_id="call-old")]),
        ModelResponse(parts=[TextPart("all set")]),
    ]
    assert PendingAskUser(completed).tool_calls() == []

    # Parallel pause: sibling tool returned, ask_user_question still pending.
    parallel_pause: list[ModelMessage] = [
        *completed,
        ModelRequest(parts=[UserPromptPart("next")]),
        ModelResponse(parts=[sibling, current]),
        ModelRequest(parts=[ToolReturnPart(tool_name="read_file", content="...", tool_call_id="call-read")]),
    ]
    assert PendingAskUser(parallel_pause).tool_calls() == [current]

    # Once answered, no pending call remains.
    answered: list[ModelMessage] = [
        *parallel_pause,
        ModelRequest(
            parts=[ToolReturnPart(tool_name=TOOL_NAME, content={"Theme": ["Dark"]}, tool_call_id="call-current")]
        ),
    ]
    assert PendingAskUser(answered).tool_calls() == []


def test_requests_skips_malformed_calls_while_tool_calls_keeps_them() -> None:
    """`tool_calls()` keeps every dangling call for closure; `requests()` skips corrupt payloads."""
    corrupt = ToolCallPart(tool_name=TOOL_NAME, args={"questions": []}, tool_call_id="call-corrupt")
    valid = make_ask_call("call-valid")
    inspector = PendingAskUser([ModelResponse(parts=[corrupt, valid])])

    assert [call.tool_call_id for call in inspector.tool_calls()] == ["call-corrupt", "call-valid"]
    assert inspector.as_payloads() == [
        {
            "tool_call_id": "call-valid",
            "questions": [
                {
                    "header": "Theme",
                    "question": "Which theme should the app use?",
                    "options": [
                        {"label": "Light (Recommended)", "description": "Bright and clean"},
                        {"label": "Dark", "description": None},
                    ],
                    "multi_select": False,
                }
            ],
        }
    ]
