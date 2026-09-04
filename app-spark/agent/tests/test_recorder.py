"""Raw transcript capture: record before compaction, persist when it rewrites history."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.capabilities import CapabilityOrdering
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestContext, ModelRequestParameters
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import RunContext

from app_spark_agent.recorder import TranscriptRecorder, record_messages
from app_spark_agent.state import AppendLog, ContextStore

_RUN_CTX = cast(RunContext[Any], object())
CONVERSATION_ID = "conv-1"
RUN_ID = "run-1"


def make_log(tmp_path: Path) -> AppendLog:
    return AppendLog(tmp_path / "log.jsonl", payload_key="message")


def make_recorder(tmp_path: Path) -> tuple[TranscriptRecorder, AppendLog, ContextStore]:
    log = make_log(tmp_path)
    store = ContextStore(tmp_path / "context.json")
    recorder = TranscriptRecorder(
        log=log,
        context_store=store,
        conversation_id=CONVERSATION_ID,
        run_id=RUN_ID,
    )
    return recorder, log, store


def request_context(messages: Sequence[ModelMessage]) -> ModelRequestContext:
    return ModelRequestContext(
        model=TestModel(),
        messages=list(messages),
        model_settings=None,
        model_request_parameters=ModelRequestParameters(),
    )


def user_turn(content: str) -> ModelRequest:
    return ModelRequest(
        parts=[UserPromptPart(content=content)],
        run_id=RUN_ID,
        conversation_id=CONVERSATION_ID,
    )


def assistant_turn(content: str) -> ModelResponse:
    return ModelResponse(
        parts=[TextPart(content=content)],
        model_name="test-fixture",
        run_id=RUN_ID,
        conversation_id=CONVERSATION_ID,
    )


def recorded(log: AppendLog) -> list[ModelMessage]:
    return ModelMessagesTypeAdapter.validate_python([record.payload for record in log.read_since(0, 1_000)])


async def test_record_messages_skips_an_empty_sequence(tmp_path: Path) -> None:
    log = make_log(tmp_path)

    await record_messages(log, RUN_ID, [])

    assert log.last_seq == 0


async def test_record_messages_appends_serialized_model_messages(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    messages: list[ModelMessage] = [user_turn("hello"), assistant_turn("world")]

    await record_messages(log, RUN_ID, messages)

    assert recorded(log) == messages
    assert all(record.run_id == RUN_ID for record in log.read_since(0, 10))


async def test_the_first_request_records_nothing_until_the_response(tmp_path: Path) -> None:
    """The caller already recorded the opening state, so the first before-hook is a no-op."""
    recorder, log, store = make_recorder(tmp_path)
    user = user_turn("hello")
    response = assistant_turn("world")

    assert recorder.get_ordering() == CapabilityOrdering(position="outermost")

    await recorder.before_model_request(_RUN_CTX, request_context([user]))
    assert recorded(log) == []
    assert recorder.compactions == 0

    await recorder.after_model_request(
        _RUN_CTX,
        request_context=request_context([user]),
        response=response,
    )
    assert recorded(log) == [response]
    assert recorder.compactions == 0
    assert store.context.is_empty


async def test_later_requests_record_the_suffix_and_ignore_a_head_summary(
    tmp_path: Path,
) -> None:
    """Compaction splices a summary at the head; only the untouched tail is new transcript."""
    recorder, log, _store = make_recorder(tmp_path)
    user = user_turn("hello")
    first_response = assistant_turn("world")
    tool_return = user_turn("tool result")
    summary = ModelRequest(parts=[SystemPromptPart(content="Summary of previous conversation:")])

    await recorder.before_model_request(_RUN_CTX, request_context([user]))
    await recorder.after_model_request(
        _RUN_CTX,
        request_context=request_context([user]),
        response=first_response,
    )

    await recorder.before_model_request(
        _RUN_CTX,
        request_context([summary, user, first_response, tool_return]),
    )

    assert recorded(log) == [first_response, tool_return]


async def test_compaction_commits_the_settled_history_mid_run(tmp_path: Path) -> None:
    recorder, log, store = make_recorder(tmp_path)
    user = user_turn("hello")
    first_response = assistant_turn("world")
    tool_return = user_turn("tool result")
    summary = ModelRequest(parts=[SystemPromptPart(content="Summary of previous conversation:")])
    compacted = [summary, tool_return]
    second_response = assistant_turn("done")

    await recorder.before_model_request(_RUN_CTX, request_context([user]))
    await recorder.after_model_request(
        _RUN_CTX,
        request_context=request_context([user]),
        response=first_response,
    )
    await recorder.before_model_request(
        _RUN_CTX,
        request_context([user, first_response, tool_return]),
    )
    await recorder.after_model_request(
        _RUN_CTX,
        request_context=request_context(compacted),
        response=second_response,
    )

    assert recorder.compactions == 1
    assert store.context.messages == compacted
    assert store.context.context_version == 1
    assert recorded(log) == [first_response, tool_return, second_response]
