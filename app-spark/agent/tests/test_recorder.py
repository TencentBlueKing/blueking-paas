"""Raw transcript capture: record before compaction, persist when it rewrites history."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from pydantic_ai import Agent, ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.capabilities import AbstractCapability, CapabilityOrdering
from pydantic_ai.messages import (
    CompactionPart,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestContext, ModelRequestParameters
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import RunContext

from app_spark_agent.agent import create_agent
from app_spark_agent.fake_model import build_fake_model
from app_spark_agent.recorder import TranscriptRecorder, record_messages
from app_spark_agent.state import AppendLog, ContextStore

CONVERSATION_ID = "conv-1"
RUN_ID = "run-1"


@dataclass
class _FakeRunContext:
    """Minimal stand-in exposing ``messages`` (persistent history) for direct hook tests."""

    messages: list[ModelMessage]


def run_context(messages: Sequence[ModelMessage]) -> RunContext[Any]:
    return cast(RunContext[Any], _FakeRunContext(messages=list(messages)))


def make_log(tmp_path: Path) -> AppendLog:
    return AppendLog(tmp_path / "log.jsonl", payload_key="message")


def make_recorder(tmp_path: Path) -> tuple[TranscriptRecorder, AppendLog, ContextStore]:
    tmp_path.mkdir(parents=True, exist_ok=True)
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
    ctx = run_context([user])

    assert recorder.get_ordering() == CapabilityOrdering(position="outermost")

    await recorder.before_model_request(ctx, request_context([user]))
    assert recorded(log) == []
    assert recorder.compactions == 0

    await recorder.after_model_request(
        ctx,
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
    summary = ModelRequest(parts=[CompactionPart(content="the conversation so far")])

    first_ctx = run_context([user])
    await recorder.before_model_request(first_ctx, request_context([user]))
    await recorder.after_model_request(
        first_ctx,
        request_context=request_context([user]),
        response=first_response,
    )

    next_history: list[ModelMessage] = [summary, user, first_response, tool_return]
    await recorder.before_model_request(
        run_context(next_history),
        request_context(next_history),
    )

    assert recorded(log) == [first_response, tool_return]


async def test_compaction_commits_the_settled_history_mid_run(tmp_path: Path) -> None:
    recorder, log, store = make_recorder(tmp_path)
    user = user_turn("hello")
    first_response = assistant_turn("world")
    tool_return = user_turn("tool result")
    summary = ModelRequest(parts=[CompactionPart(content="the conversation so far")])
    compacted: list[ModelMessage] = [summary, tool_return]
    second_response = assistant_turn("done")

    first_ctx = run_context([user])
    await recorder.before_model_request(first_ctx, request_context([user]))
    await recorder.after_model_request(
        first_ctx,
        request_context=request_context([user]),
        response=first_response,
    )

    second_ctx = run_context([user, first_response, tool_return])
    await recorder.before_model_request(
        second_ctx,
        request_context(second_ctx.messages),
    )
    # Real compaction mutates persistent history (`ctx.messages[:] = compacted`).
    second_ctx.messages[:] = compacted
    await recorder.after_model_request(
        second_ctx,
        request_context=request_context(compacted),
        response=second_response,
    )

    assert recorder.compactions == 1
    assert store.context.messages == compacted
    assert store.context.context_version == 1
    assert recorded(log) == [first_response, tool_return, second_response]


async def test_request_only_message_rewrites_do_not_trigger_compaction(tmp_path: Path) -> None:
    """Rewriting ``request_context.messages`` without touching ``ctx.messages`` is not compaction."""
    recorder, log, store = make_recorder(tmp_path)
    user = user_turn("hello")
    wire_copy = replace(user, instructions="<context id='capability:repo_context'>...</context>")
    response = assistant_turn("world")
    ctx = run_context([user])

    await recorder.before_model_request(ctx, request_context([user]))
    # Wire projection / request-only hooks replace objects in `request_context.messages` only.
    await recorder.after_model_request(
        ctx,
        request_context=request_context([wire_copy]),
        response=response,
    )

    assert recorder.compactions == 0
    assert store.context.is_empty
    assert recorded(log) == [response]


async def test_deferred_resume_records_messages_past_initial_message_count(tmp_path: Path) -> None:
    """Deferred-resume runs pre-record nothing, so the first request must capture the new tool return."""
    log = make_log(tmp_path)
    store = ContextStore(tmp_path / "context.json")
    prior_user = user_turn("first")
    prior_response = assistant_turn("asking")
    deferred_return = user_turn("answered")
    final_response = assistant_turn("done")
    recorder = TranscriptRecorder(
        log=log,
        context_store=store,
        conversation_id=CONVERSATION_ID,
        run_id=RUN_ID,
        initial_message_count=2,
    )
    ctx = run_context([prior_user, prior_response, deferred_return])

    await recorder.before_model_request(ctx, request_context(ctx.messages))
    await recorder.after_model_request(
        ctx,
        request_context=request_context(ctx.messages),
        response=final_response,
    )

    assert recorded(log) == [deferred_return, final_response]


async def test_flush_trailing_records_post_response_messages_once(tmp_path: Path) -> None:
    """A run pausing on a deferred tool after a sibling tool leaves an unrecorded trailing request."""
    recorder, log, _store = make_recorder(tmp_path)
    user = user_turn("hello")
    response = assistant_turn("calling tools")
    sibling_return = user_turn("sibling tool result")
    ctx = run_context([user])

    await recorder.before_model_request(ctx, request_context([user]))
    await recorder.after_model_request(ctx, request_context=request_context([user]), response=response)

    await recorder.flush_trailing([user, response, sibling_return])
    await recorder.flush_trailing([user, response, sibling_return])

    assert recorded(log) == [response, sibling_return]


async def test_wire_instruction_projection_and_nested_agents_md_do_not_trigger_compaction(
    tmp_path: Path,
) -> None:
    """Full ``create_agent`` (with ``RepoContext`` + nested ``AGENTS.md``) must not false-compact."""
    workspace = tmp_path / "workspace"
    sub = workspace / "sub"
    sub.mkdir(parents=True)
    (sub / "AGENTS.md").write_text("Follow local rules.\n")
    (sub / "note.txt").write_text("hello\n")

    step = 0

    async def stream_fn(_messages: list[ModelMessage], _info: Any) -> Any:
        nonlocal step
        step += 1
        if step == 1:
            yield {0: DeltaToolCall(name="read_file", json_args='{"path": "sub/note.txt"}', tool_call_id="c1")}
        else:
            yield "all read"

    recorder, log, store = make_recorder(tmp_path)
    agent = create_agent(workspace=workspace)

    await agent.run(
        "read sub/note.txt",
        model=FunctionModel(stream_function=stream_fn),
        capabilities=[recorder],
        conversation_id=CONVERSATION_ID,
    )

    assert step == 2
    assert recorder.compactions == 0
    assert store.context.is_empty
    # Two model responses + one tool-return request + one nested AGENTS.md note, never duplicated.
    assert len(recorded(log)) == 4


async def test_prepare_model_request_compaction_and_request_only_rewrites_are_distinguished(
    tmp_path: Path,
) -> None:
    """Compaction inside ``prepare_model_request`` commits; request-only rewrites never do."""

    class RequestOnlyRewriter(AbstractCapability[Any]):
        async def before_model_request(
            self,
            ctx: RunContext[Any],
            request_context: ModelRequestContext,
        ) -> ModelRequestContext:
            return replace(
                request_context,
                messages=[replace(m) if isinstance(m, ModelRequest) else m for m in request_context.messages],
            )

    class PreparePhaseCompactor(AbstractCapability[Any]):
        async def prepare_model_request(
            self,
            ctx: RunContext[Any],
            request_context: ModelRequestContext,
        ) -> ModelRequestContext:
            compacted: list[ModelMessage] = [
                ModelRequest(parts=[CompactionPart(content="compacted in prepare_model_request")]),
                *ctx.messages[-1:],
            ]
            ctx.messages[:] = compacted
            return replace(request_context, messages=compacted)

    recorder1, _log1, store1 = make_recorder(tmp_path / "req_only")
    agent1 = Agent(build_fake_model("chat"), capabilities=[RequestOnlyRewriter(), recorder1])
    await agent1.run("hi", conversation_id=CONVERSATION_ID)
    assert recorder1.compactions == 0
    assert store1.context.is_empty

    recorder2, _log2, store2 = make_recorder(tmp_path / "prepare_compact")
    agent2 = Agent(build_fake_model("chat"), capabilities=[PreparePhaseCompactor(), recorder2])
    await agent2.run("hi", conversation_id=CONVERSATION_ID)
    assert recorder2.compactions == 1
    assert store2.context.context_version == 1
