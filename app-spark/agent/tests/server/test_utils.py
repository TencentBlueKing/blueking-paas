"""Unit tests for :mod:`app_spark_agent.server.utils`."""

from __future__ import annotations

from collections.abc import AsyncIterator

from ag_ui.core import BaseEvent, RunFinishedEvent, RunStartedEvent, ToolCallResultEvent

from app_spark_agent.server.utils import inject_after_run_started


async def test_inject_after_run_started_inserts_only_after_run_started() -> None:
    started = RunStartedEvent(thread_id="t1", run_id="r1")
    finished = RunFinishedEvent(thread_id="t1", run_id="r1")
    injected = ToolCallResultEvent(message_id="m1", tool_call_id="call-1", content="closed", role="tool")

    async def stream(*events: BaseEvent) -> AsyncIterator[BaseEvent]:
        for event in events:
            yield event

    assert [e async for e in inject_after_run_started(stream(started, finished), [injected])] == [
        started,
        injected,
        finished,
    ]
    assert [e async for e in inject_after_run_started(stream(started, finished), [])] == [
        started,
        finished,
    ]
    assert [e async for e in inject_after_run_started(stream(finished), [injected])] == [finished]
