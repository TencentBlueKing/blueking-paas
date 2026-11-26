"""End-to-end Runtime HTTP/SSE tests for `AskUser(answerer=None)` pause/resume and chat bypass."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel
from pydantic_ai_harness import AskUser
from pydantic_ai_harness.ask_user import DECLINED, TOOL_NAME

from app_spark_agent.cap.ask_user import BYPASSED_BY_USER_MESSAGE
from app_spark_agent.state import ConversationContext
from tests.api.support import (
    answer_request,
    answer_turn,
    build_test_client,
    drain_channel,
    get_context,
    get_transcript_messages,
    http_client,
    run_turn,
    wait_until_busy,
)
from tests.support.ag_ui import SSE_HEADERS, answer_run_body, run_body

SAMPLE_QUESTIONS: list[dict[str, object]] = [
    {
        "header": "Style",
        "question": "Which style fits best?",
        "options": [
            {"label": "Clean (Recommended)", "description": "Minimal and focused"},
            {"label": "Bold", "description": "Vibrant colors"},
        ],
        "multi_select": False,
    },
    {
        "header": "Features",
        "question": "Which features do you want?",
        "options": [
            {"label": "Search", "description": "Instant keyword filter"},
            {"label": "Export", "description": "Download CSV"},
        ],
        "multi_select": True,
    },
]


def build_ask_user_client(
    tmp_path: Path,
    *,
    model: Model,
    tools: Sequence[Any] = (),
) -> TestClient:
    """Build a Runtime whose Agent has `AskUser(answerer=None)` enabled."""
    return build_test_client(
        tmp_path,
        model=model,
        tools=tools,
        capabilities=[AskUser(answerer=None)],
        output_type=[str, DeferredToolRequests],
    )


def ask_once_model(
    *,
    tool_call_id: str = "call-ask-1",
    sibling_tool_name: str | None = None,
    resume_started: asyncio.Event | None = None,
    resume_gate: asyncio.Event | None = None,
) -> FunctionModel:
    """Issue `ask_user_question` on the first model call, then echo what arrived on resume."""

    async def stream(messages: list[ModelMessage], _info: AgentInfo) -> AsyncIterator[str | DeltaToolCalls]:
        ask_returns = [
            part
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, ToolReturnPart) and part.tool_name == TOOL_NAME
        ]
        if not ask_returns:
            calls: dict[int, DeltaToolCall] = {}
            index = 0
            if sibling_tool_name is not None:
                calls[index] = DeltaToolCall(
                    name=sibling_tool_name,
                    json_args="{}",
                    tool_call_id="call-sibling-1",
                )
                index += 1
            calls[index] = DeltaToolCall(
                name=TOOL_NAME,
                json_args=json.dumps({"questions": SAMPLE_QUESTIONS}),
                tool_call_id=tool_call_id,
            )
            yield calls
            return

        if resume_gate is not None:
            yield "working "
            if resume_started is not None:
                resume_started.set()
            await resume_gate.wait()
            yield "finished"
            return

        user_prompts = [
            part.content
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart)
        ]
        yield f"ANSWER={ask_returns[-1].content!r} PROMPTS={user_prompts!r}"

    return FunctionModel(stream_function=stream)


def test_ask_user_pauses_cleanly_and_resumes_with_selected_options(tmp_path: Path) -> None:
    client = build_ask_user_client(tmp_path, model=ask_once_model())
    conversation_id = str(uuid4())

    paused = run_turn(client, conversation_id=conversation_id, prompt="build a tracker")

    assert paused.event_types[0] == "RUN_STARTED"
    assert "TOOL_CALL_START" in paused.event_types
    assert "TOOL_CALL_RESULT" not in paused.event_types
    assert paused.events[-1]["type"] == "RUN_FINISHED"
    assert paused.events[-1]["outcome"] == {
        "type": "success",
        "pendingToolCallIds": ["call-ask-1"],
    }

    health_paused: dict[str, Any] = client.get("/health").json()
    assert health_paused["running"] is False
    assert health_paused["context_version"] == 1
    assert len(health_paused["pending_questions"]) == 1
    assert health_paused["pending_questions"][0]["tool_call_id"] == "call-ask-1"
    assert [q["header"] for q in health_paused["pending_questions"][0]["questions"]] == ["Style", "Features"]

    resumed = answer_turn(
        client,
        conversation_id=conversation_id,
        responses=[
            {
                "toolCallId": "call-ask-1",
                "answers": [
                    {"header": "Style", "selected": ["Bold"]},
                    {"header": "Features", "selected": ["Search", "Export"]},
                ],
            }
        ],
    )

    tool_results = [event for event in resumed.events if event["type"] == "TOOL_CALL_RESULT"]
    assert len(tool_results) == 1
    assert tool_results[0]["toolCallId"] == "call-ask-1"
    assert json.loads(tool_results[0]["content"]) == {"Style": ["Bold"], "Features": ["Search", "Export"]}
    assert resumed.events[-1]["outcome"] == {"type": "success"}
    assert "{'Style': ['Bold'], 'Features': ['Search', 'Export']}" in resumed.reply

    health_resumed: dict[str, Any] = client.get("/health").json()
    assert health_resumed["running"] is False
    assert health_resumed["context_version"] == 2
    assert health_resumed["pending_questions"] == []

    # Raw transcript must capture the deferred tool return alongside the model responses.
    transcript = get_transcript_messages(client)
    assert [msg["kind"] for msg in transcript] == ["request", "response", "request", "response"]
    assert transcript[2]["parts"][0]["part_kind"] == "tool-return"
    assert transcript[2]["parts"][0]["tool_call_id"] == "call-ask-1"


@pytest.mark.parametrize(
    ("response_item", "expected_snippet", "expected_tool_content"),
    [
        pytest.param(
            {
                "toolCallId": "call-ask-1",
                "answers": [
                    {"header": "Style", "customAnswer": "Retro terminal green"},
                    {"header": "Features", "customAnswer": "Keyboard shortcuts only"},
                ],
            },
            "Retro terminal green",
            None,
            id="custom-answer",
        ),
        pytest.param(
            {"toolCallId": "call-ask-1", "cancelled": True},
            DECLINED,
            DECLINED,
            id="cancelled-skip",
        ),
    ],
)
def test_ask_user_resumes_with_custom_answer_or_skip(
    tmp_path: Path,
    response_item: dict[str, object],
    expected_snippet: str,
    expected_tool_content: str | None,
) -> None:
    client = build_ask_user_client(tmp_path, model=ask_once_model())
    conversation_id = str(uuid4())
    run_turn(client, conversation_id=conversation_id, prompt="build a page")

    resumed = answer_turn(client, conversation_id=conversation_id, responses=[response_item])

    if expected_tool_content is not None:
        tool_result = next(event for event in resumed.events if event["type"] == "TOOL_CALL_RESULT")
        assert tool_result["content"] == expected_tool_content
    assert expected_snippet in resumed.reply
    assert client.get("/health").json()["pending_questions"] == []


def test_sending_normal_chat_message_bypasses_pending_question_in_valid_order(tmp_path: Path) -> None:
    """Ignoring the question card and chatting directly closes the tool call before the new user turn."""
    client = build_ask_user_client(tmp_path, model=ask_once_model())
    conversation_id = str(uuid4())

    run_turn(client, conversation_id=conversation_id, prompt="build an app")
    assert len(client.get("/health").json()["pending_questions"]) == 1

    bypassed = run_turn(client, conversation_id=conversation_id, prompt="actually make a simple calculator")

    # SSE stream (and ui_events) must emit TOOL_CALL_RESULT right after RUN_STARTED so the card closes.
    assert bypassed.event_types[0] == "RUN_STARTED"
    assert bypassed.event_types[1] == "TOOL_CALL_RESULT"
    assert bypassed.events[1]["toolCallId"] == "call-ask-1"
    assert bypassed.events[1]["content"] == BYPASSED_BY_USER_MESSAGE
    assert "actually make a simple calculator" in bypassed.reply
    assert BYPASSED_BY_USER_MESSAGE in bypassed.reply
    assert client.get("/health").json()["pending_questions"] == []

    # Persisted ui-events channel matches what was streamed.
    stored_ui_events = [record["event"] for record in drain_channel(client, "/ui-events")]
    closing_events = [
        event
        for event in stored_ui_events
        if event.get("type") == "TOOL_CALL_RESULT" and event.get("toolCallId") == "call-ask-1"
    ]
    assert len(closing_events) == 1
    assert closing_events[0]["content"] == BYPASSED_BY_USER_MESSAGE

    # Transcript and context must preserve assistant(tool_calls) -> tool(return) -> user(new msg).
    transcript = get_transcript_messages(client)
    assert [msg["kind"] for msg in transcript] == ["request", "response", "request", "request", "response"]
    assert transcript[2]["parts"][0]["part_kind"] == "tool-return"
    assert transcript[2]["parts"][0]["content"] == BYPASSED_BY_USER_MESSAGE
    assert transcript[3]["parts"][0]["part_kind"] == "user-prompt"
    assert transcript[3]["parts"][0]["content"] == "actually make a simple calculator"

    context = ConversationContext.from_payload(get_context(client))
    message_shape = [(type(msg), [type(part) for part in msg.parts]) for msg in context.messages]
    assert message_shape == [
        (ModelRequest, [UserPromptPart]),
        (ModelResponse, [ToolCallPart]),
        (ModelRequest, [ToolReturnPart, UserPromptPart]),
        (ModelResponse, [TextPart]),
    ]


def test_parallel_sibling_tool_and_ask_user_records_complete_transcript(tmp_path: Path) -> None:
    """When a sibling tool runs alongside a deferred ask_user_question, its return is still recorded."""

    def inspect_env() -> str:
        return "workspace-ok"

    client = build_ask_user_client(
        tmp_path,
        model=ask_once_model(sibling_tool_name="inspect_env"),
        tools=[inspect_env],
    )
    conversation_id = str(uuid4())

    paused = run_turn(client, conversation_id=conversation_id, prompt="check and ask")
    assert paused.events[-1]["outcome"] == {"type": "success", "pendingToolCallIds": ["call-ask-1"]}
    assert len(client.get("/health").json()["pending_questions"]) == 1

    # Sibling tool return must already be in log.jsonl even before the question is answered.
    transcript_paused = get_transcript_messages(client)
    assert [msg["kind"] for msg in transcript_paused] == ["request", "response", "request"]
    assert transcript_paused[2]["parts"][0]["tool_name"] == "inspect_env"
    assert transcript_paused[2]["parts"][0]["content"] == "workspace-ok"

    answer_turn(
        client,
        conversation_id=conversation_id,
        responses=[{"toolCallId": "call-ask-1", "cancelled": True}],
    )

    transcript_resumed = get_transcript_messages(client)
    assert [msg["kind"] for msg in transcript_resumed] == ["request", "response", "request", "request", "response"]
    assert transcript_resumed[3]["parts"][0]["tool_name"] == TOOL_NAME
    assert transcript_resumed[3]["parts"][0]["content"] == DECLINED


def test_cold_start_context_restore_preserves_pending_questions_and_resumes(tmp_path: Path) -> None:
    """A freshly started Runtime restored via `PUT /context` can immediately resume a paused question."""
    conversation_id = str(uuid4())
    first_runtime = build_ask_user_client(tmp_path / "r1", model=ask_once_model())
    run_turn(first_runtime, conversation_id=conversation_id, prompt="build an app")

    archived_context = get_context(first_runtime)
    first_health: dict[str, Any] = first_runtime.get("/health").json()

    second_runtime = build_ask_user_client(tmp_path / "r2", model=ask_once_model())
    restore_resp = second_runtime.put(
        "/context",
        params={"log_seq": first_health["log_seq"], "ui_event_seq": first_health["ui_event_seq"]},
        json=archived_context,
    )
    assert restore_resp.status_code == 200, restore_resp.text

    restored_health: dict[str, Any] = second_runtime.get("/health").json()
    assert len(restored_health["pending_questions"]) == 1
    assert restored_health["pending_questions"][0]["tool_call_id"] == "call-ask-1"

    resumed = answer_turn(
        second_runtime,
        conversation_id=conversation_id,
        responses=[
            {
                "toolCallId": "call-ask-1",
                "answers": [
                    {"header": "Style", "selected": ["Clean (Recommended)"]},
                    {"header": "Features", "selected": ["Search"]},
                ],
            }
        ],
    )
    assert "Clean (Recommended)" in resumed.reply
    assert second_runtime.get("/health").json()["pending_questions"] == []


def test_answer_validation_and_conflict_status_codes(tmp_path: Path) -> None:
    client = build_ask_user_client(tmp_path, model=ask_once_model())
    conversation_id = str(uuid4())

    # Answering when no question is pending -> 409 Conflict.
    no_pending = answer_request(
        client,
        conversation_id=conversation_id,
        context_version=0,
        responses=[{"toolCallId": "call-ask-1", "cancelled": True}],
    )
    assert no_pending.status_code == 409

    # Pause with a real question.
    run_turn(client, conversation_id=conversation_id, prompt="build an app")

    # Combining messages + askUserResponses -> 422.
    mixed_body = run_body(conversation_id=conversation_id, run_id=str(uuid4()), context_version=1, prompt="hi")
    mixed_body["forwardedProps"] = {
        **cast(dict[str, object], mixed_body["forwardedProps"]),
        "askUserResponses": [{"toolCallId": "call-ask-1", "cancelled": True}],
    }
    mixed = client.post("/runs", headers=SSE_HEADERS, json=mixed_body)
    assert mixed.status_code == 422

    # Unknown toolCallId -> 409.
    wrong_id = answer_request(
        client,
        conversation_id=conversation_id,
        context_version=1,
        responses=[{"toolCallId": "call-other", "cancelled": True}],
    )
    assert wrong_id.status_code == 409

    # Invalid option -> 422.
    bad_option = answer_request(
        client,
        conversation_id=conversation_id,
        context_version=1,
        responses=[
            {
                "toolCallId": "call-ask-1",
                "answers": [
                    {"header": "Style", "selected": ["Unknown"]},
                    {"header": "Features", "selected": ["Search"]},
                ],
            }
        ],
    )
    assert bad_option.status_code == 422


async def test_stopping_a_resumed_run_keeps_the_answered_question_closed(tmp_path: Path) -> None:
    started = asyncio.Event()
    gate = asyncio.Event()
    test_client = build_ask_user_client(tmp_path, model=ask_once_model(resume_started=started, resume_gate=gate))
    conversation_id = str(uuid4())
    run_turn(test_client, conversation_id=conversation_id, prompt="build an app")

    resume_run_id = str(uuid4())
    async with http_client(test_client) as client:
        streaming = asyncio.create_task(
            client.post(
                "/runs",
                headers=SSE_HEADERS,
                json=answer_run_body(
                    conversation_id=conversation_id,
                    run_id=resume_run_id,
                    context_version=1,
                    responses=[{"toolCallId": "call-ask-1", "cancelled": True}],
                ),
            )
        )
        try:
            await wait_until_busy(client)
            await asyncio.wait_for(started.wait(), timeout=5.0)
            stop_resp = await client.post(f"/runs/{resume_run_id}/stop")
            assert stop_resp.status_code == 202
        finally:
            gate.set()

        response = await streaming
        assert response.status_code == 200
        health: dict[str, Any] = (await client.get("/health")).json()

    assert health["running"] is False
    assert health["pending_questions"] == []
    # Confirm the paused tool call has a matching tool-return in committed context.
    context = ConversationContext.from_payload(get_context(test_client))
    tool_call_ids = {
        part.tool_call_id for msg in context.messages for part in msg.parts if isinstance(part, ToolCallPart)
    }
    tool_return_ids = {
        part.tool_call_id for msg in context.messages for part in msg.parts if isinstance(part, ToolReturnPart)
    }
    assert tool_call_ids == {"call-ask-1"}
    assert tool_return_ids == {"call-ask-1"}
