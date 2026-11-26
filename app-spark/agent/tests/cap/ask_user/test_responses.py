"""Contract tests for :func:`app_spark_agent.cap.ask_user.build_ask_user_deferred_results`."""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ToolCallPart
from pydantic_ai_harness.ask_user import TOOL_NAME

from app_spark_agent.cap.ask_user import (
    AskUserConflictError,
    AskUserValidationError,
    build_ask_user_deferred_results,
)


def make_ask_call(tool_call_id: str = "call-1") -> ToolCallPart:
    return ToolCallPart(
        tool_name=TOOL_NAME,
        args={
            "questions": [
                {
                    "header": "Theme",
                    "question": "Which theme?",
                    "options": [{"label": "Light"}, {"label": "Dark"}],
                }
            ]
        },
        tool_call_id=tool_call_id,
    )


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param("not-a-list", id="not-a-list"),
        pytest.param([], id="empty-list"),
        pytest.param([{"toolCallId": "call-1", "cancelled": "true"}], id="strict-bool-type"),
        pytest.param(
            [{"toolCallId": "call-1", "answers": [{"header": "Theme", "selected": ["Dark"], "note": "extra"}]}],
            id="forbids-unsupported-note-field",
        ),
        pytest.param(
            [
                {"toolCallId": "call-1", "cancelled": True},
                {"toolCallId": "call-1", "cancelled": True},
            ],
            id="duplicate-tool-call-id",
        ),
        pytest.param(
            [{"toolCallId": "call-1", "answers": [{"header": "Theme", "selected": ["Unknown"]}]}],
            id="propagates-upstream-answer-validation-error",
        ),
    ],
)
def test_rejects_invalid_wire_payloads_as_validation_error(payload: object) -> None:
    with pytest.raises(AskUserValidationError):
        build_ask_user_deferred_results(payload, [make_ask_call("call-1")])


def test_requires_every_pending_call_to_be_answered() -> None:
    with pytest.raises(AskUserValidationError, match="call-2"):
        build_ask_user_deferred_results(
            [{"toolCallId": "call-1", "cancelled": True}],
            [make_ask_call("call-1"), make_ask_call("call-2")],
        )


def test_raises_conflict_when_no_question_is_pending_or_id_does_not_match() -> None:
    with pytest.raises(AskUserConflictError, match="no pending questions"):
        build_ask_user_deferred_results([{"toolCallId": "call-1", "cancelled": True}], [])

    with pytest.raises(AskUserConflictError, match="call-other"):
        build_ask_user_deferred_results([{"toolCallId": "call-other", "cancelled": True}], [make_ask_call("call-1")])
