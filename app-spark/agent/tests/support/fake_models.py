"""Deterministic models and tools shared by Runtime tests."""

import asyncio
import json
from collections.abc import AsyncIterator, Sequence

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel

# Big enough that a handful of tool results dominate the estimated token count, so a low
# compaction target is reached by clearing them rather than by anything else.
PROBE_PAYLOAD = "x" * 400

PROBE_TOOL = "probe"


def probe(index: int) -> str:
    """Return a payload large enough for compaction to want to reclaim it."""
    return f"probe-payload-{index}-{PROBE_PAYLOAD}"


def log_calling_model() -> FunctionModel:
    """Call read_app_log once, then answer after the structured result comes back."""
    issued = False

    async def stream(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        nonlocal issued
        if not issued:
            issued = True
            yield {0: DeltaToolCall(name="read_app_log", json_args="{}", tool_call_id="app-log-1")}
            return
        yield "log-consumed"

    return FunctionModel(stream_function=stream)


def tool_calling_model(rounds: int) -> FunctionModel:
    """Build a model that calls probe rounds times and then answers with text.

    The remaining rounds are tracked in the closure rather than counted from the history: a
    compaction tier that drops or blanks the earlier turns would otherwise reset the count and
    leave the fake model looping forever.
    """
    issued = 0

    async def stream(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        nonlocal issued
        if issued >= rounds:
            yield "done"
            return
        index = issued
        issued += 1
        yield {
            0: DeltaToolCall(
                name=PROBE_TOOL,
                json_args=json.dumps({"index": index}),
                tool_call_id=f"probe-call-{index}",
            )
        }

    return FunctionModel(stream_function=stream)


def text_model(chunks: Sequence[str]) -> FunctionModel:
    """Build a model that streams chunks as one assistant message."""

    async def stream(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        for chunk in chunks:
            yield chunk

    return FunctionModel(stream_function=stream)


def summarizing_model(summary: str) -> FunctionModel:
    """Build the dedicated model a summarizing compaction tier calls.

    A tier without its own model borrows the run's, which would hand the summary request to a
    fake that only knows how to call tools.
    """

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=summary)])

    return FunctionModel(respond)


def failing_model(*, message: str = "synthetic model failure") -> FunctionModel:
    """Build a model that fails the first request, so the run never completes."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError(message)

    return FunctionModel(respond)


def tool_then_fail_model(*, tool_rounds: int = 2) -> FunctionModel:
    """Call probe tool_rounds times, then raise so the run ends unsuccessfully.

    Used to leave a mid-run compaction on disk: the tool rounds succeed and may
    persist a compacted context, then the next request blows up before
    on_complete.
    """
    issued = 0

    async def stream(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        nonlocal issued
        if issued >= tool_rounds:
            raise RuntimeError("fail after tool rounds")
        index = issued
        issued += 1
        yield {
            0: DeltaToolCall(
                name=PROBE_TOOL,
                json_args=json.dumps({"index": index}),
                tool_call_id=f"probe-call-{index}",
            )
        }

    return FunctionModel(stream_function=stream)


def gated_model(gate: asyncio.Event, *, reply: str = "done") -> FunctionModel:
    """Build a model that holds its response open until gate is set.

    A run occupies the Runtime for exactly as long as its model keeps producing output, so this
    is what lets a test send a request *while* a run is in flight rather than after it ended.
    """

    async def stream(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        await gate.wait()
        yield reply

    return FunctionModel(stream_function=stream)
