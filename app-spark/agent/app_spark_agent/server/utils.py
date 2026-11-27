"""Generic HTTP/AG-UI stream helpers shared inside :mod:`app_spark_agent.server`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from ag_ui.core import BaseEvent, RunStartedEvent


async def inject_after_run_started(
    events: AsyncIterator[BaseEvent],
    injected: Sequence[BaseEvent],
) -> AsyncIterator[BaseEvent]:
    """Yield ``injected`` events immediately after the first ``RUN_STARTED`` event.

    Leaves the stream untouched when ``injected`` is empty. Inserting right after ``RUN_STARTED``
    keeps every injected event inside the run's AG-UI envelope so both live SSE subscribers and
    ``ui_events.jsonl`` replay observe a well-formed sequence.
    """
    if not injected:
        async for event in events:
            yield event
        return

    inserted = False
    async for event in events:
        yield event
        if not inserted and isinstance(event, RunStartedEvent):
            inserted = True
            for extra in injected:
                yield extra
