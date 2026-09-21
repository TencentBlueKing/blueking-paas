"""Persist the AG-UI event history the client actually saw.

The stored copy is masked; the live stream is forwarded untouched. That split is deliberate.
Masking each delta as it goes past would run on every streamed token to catch a value that can
only be there if credential stripping had already failed, and it would still miss the value
whenever the model happened to split it across two chunks. The stored copy is coalesced per
message before it is masked, so it has the whole string to match against, and it is the copy an
audit reads. A client that sees a credential in its own stream is a client that already holds
one.
"""

from collections.abc import AsyncIterator, Sequence
from enum import StrEnum

from ag_ui.core import (
    BaseEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
)

from app_spark_agent.masking import mask_payload
from app_spark_agent.state import AppendLog


class _Family(StrEnum):
    """A group of AG-UI events that stream one value in deltas until a matching end event."""

    TEXT = "text"
    TOOL_ARGS = "toolArgs"
    THINKING = "thinking"
    REASONING = "reasoning"


# The thinking family carries no identifier, so its buffer needs a fixed key.
_SINGLETON = ""

_Buffers = dict[tuple[_Family, str], list[str]]


async def record_ui_events(
    stream: AsyncIterator[BaseEvent],
    *,
    log: AppendLog,
    run_id: str,
) -> AsyncIterator[BaseEvent]:
    """Forward every AG-UI event untouched while persisting a coalesced copy of the stream.

    The client keeps its token-by-token deltas; the log stores one assembled event per streamed
    message instead of thousands of one-token rows. What is stored is still a valid AG-UI event
    sequence, so replaying it on a cold start reproduces the same UI -- which is the only way to
    get there, since message ids are random UUIDs generated per stream and cannot be recomputed
    from the model history.
    """
    buffers: _Buffers = {}
    try:
        async for event in stream:
            yield event
            await _persist(_coalesce(event, buffers), log=log, run_id=run_id)
    finally:
        # Only reached with a non-empty buffer when the stream was truncated (a client
        # disconnect mid-message). Terminating the open message keeps the stored sequence
        # replayable instead of leaving a message that never ends.
        await _persist(_terminate_open(buffers), log=log, run_id=run_id)


def _coalesce(event: BaseEvent, buffers: _Buffers) -> list[BaseEvent]:
    """Return what to store for ``event``: nothing for a delta, the whole message at its end."""
    match event:
        case TextMessageContentEvent():
            buffers.setdefault((_Family.TEXT, event.message_id), []).append(event.delta)
            return []
        case TextMessageEndEvent():
            return [*_assembled(buffers, _Family.TEXT, event.message_id), event]

        case ToolCallArgsEvent():
            buffers.setdefault((_Family.TOOL_ARGS, event.tool_call_id), []).append(event.delta)
            return []
        case ToolCallEndEvent():
            return [*_assembled(buffers, _Family.TOOL_ARGS, event.tool_call_id), event]

        case ThinkingTextMessageContentEvent():
            buffers.setdefault((_Family.THINKING, _SINGLETON), []).append(event.delta)
            return []
        case ThinkingTextMessageEndEvent():
            return [*_assembled(buffers, _Family.THINKING, _SINGLETON), event]

        case ReasoningMessageContentEvent():
            buffers.setdefault((_Family.REASONING, event.message_id), []).append(event.delta)
            return []
        case ReasoningMessageEndEvent():
            return [*_assembled(buffers, _Family.REASONING, event.message_id), event]

        case _:
            return [event]


def _assembled(buffers: _Buffers, family: _Family, key: str) -> list[BaseEvent]:
    """Return the single content event holding everything buffered for one message."""
    deltas = buffers.pop((family, key), [])
    if not deltas:
        return []
    return [_content_event(family, key, "".join(deltas))]


def _terminate_open(buffers: _Buffers) -> list[BaseEvent]:
    """Return content and end events closing every message left open by a truncated stream."""
    events: list[BaseEvent] = []
    for family, key in list(buffers):
        events.extend(_assembled(buffers, family, key))
        events.append(_end_event(family, key))
    return events


def _content_event(family: _Family, key: str, content: str) -> BaseEvent:
    match family:
        case _Family.TEXT:
            return TextMessageContentEvent(message_id=key, delta=content)
        case _Family.TOOL_ARGS:
            return ToolCallArgsEvent(tool_call_id=key, delta=content)
        case _Family.THINKING:
            return ThinkingTextMessageContentEvent(delta=content)
        case _Family.REASONING:
            return ReasoningMessageContentEvent(message_id=key, delta=content)


def _end_event(family: _Family, key: str) -> BaseEvent:
    match family:
        case _Family.TEXT:
            return TextMessageEndEvent(message_id=key)
        case _Family.TOOL_ARGS:
            return ToolCallEndEvent(tool_call_id=key)
        case _Family.THINKING:
            return ThinkingTextMessageEndEvent()
        case _Family.REASONING:
            return ReasoningMessageEndEvent(message_id=key)


async def persist_ui_events(events: Sequence[BaseEvent], *, log: AppendLog, run_id: str) -> None:
    """Write AG-UI events to the durable log without streaming them."""
    await _persist(events, log=log, run_id=run_id)


async def _persist(events: Sequence[BaseEvent], *, log: AppendLog, run_id: str) -> None:
    if not events:
        return
    # Matches how the AG-UI encoder puts an event on the wire, so a stored event and a streamed
    # one are the same JSON document, apart from the masking. Masked whole rather than per
    # field: by this point the deltas of one message are joined, so however the model chose to
    # chunk a credential, it is a single string here.
    await log.append(
        run_id,
        [mask_payload(event.model_dump(mode="json", by_alias=True, exclude_none=True)) for event in events],
    )
