"""AG-UI event logging: forward the live stream, persist a coalesced replayable copy."""

from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)

from app_spark_agent.state import AppendLog
from app_spark_agent.ui_events import persist_ui_events, record_ui_events

RUN_ID = "run-a"


def make_log(tmp_path: Path) -> AppendLog:
    return AppendLog(tmp_path / "ui_events.jsonl", payload_key="event")


def dump_event(event: BaseEvent) -> dict[str, object]:
    return event.model_dump(mode="json", by_alias=True, exclude_none=True)


def stored_events(log: AppendLog) -> list[dict[str, object]]:
    return [record.payload for record in log.read_since(0, 1_000)]


async def forward_and_record(
    events: Sequence[BaseEvent],
    log: AppendLog,
    *,
    run_id: str = RUN_ID,
) -> list[BaseEvent]:
    async def stream() -> AsyncIterator[BaseEvent]:
        for event in events:
            yield event

    forwarded: list[BaseEvent] = []
    async for event in record_ui_events(stream(), log=log, run_id=run_id):
        forwarded.append(event)
    return forwarded


async def test_every_event_is_forwarded_untouched(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    events: list[BaseEvent] = [
        TextMessageStartEvent(message_id="m1"),
        TextMessageContentEvent(message_id="m1", delta="he"),
        TextMessageContentEvent(message_id="m1", delta="llo"),
        TextMessageEndEvent(message_id="m1"),
    ]

    forwarded = await forward_and_record(events, log)

    assert forwarded == events
    assert all(got is original for got, original in zip(forwarded, events, strict=True))


async def test_text_deltas_are_stored_as_one_assembled_message(tmp_path: Path) -> None:
    """The client keeps token-by-token deltas; the log stores one content event plus its end."""
    log = make_log(tmp_path)
    start = TextMessageStartEvent(message_id="m1")
    end = TextMessageEndEvent(message_id="m1")

    await forward_and_record(
        [
            start,
            TextMessageContentEvent(message_id="m1", delta="he"),
            TextMessageContentEvent(message_id="m1", delta="llo"),
            end,
        ],
        log,
    )

    assert stored_events(log) == [
        dump_event(start),
        dump_event(TextMessageContentEvent(message_id="m1", delta="hello")),
        dump_event(end),
    ]


async def test_pass_through_events_are_stored_immediately(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    started = RunStartedEvent(thread_id="conv-1", run_id=RUN_ID)

    await forward_and_record([started], log)

    assert stored_events(log) == [dump_event(started)]


async def test_open_families_coalesce_independently(tmp_path: Path) -> None:
    """Text, tool args, thinking, and reasoning each buffer until their own end event."""
    log = make_log(tmp_path)
    text_start = TextMessageStartEvent(message_id="m1")
    text_end = TextMessageEndEvent(message_id="m1")
    tool_start = ToolCallStartEvent(tool_call_id="t1", tool_call_name="probe")
    tool_end = ToolCallEndEvent(tool_call_id="t1")
    thinking_end = ThinkingTextMessageEndEvent()
    reasoning_end = ReasoningMessageEndEvent(message_id="r1")

    await forward_and_record(
        [
            text_start,
            TextMessageContentEvent(message_id="m1", delta="hi"),
            tool_start,
            ToolCallArgsEvent(tool_call_id="t1", delta='{"n":'),
            ThinkingTextMessageContentEvent(delta="hmm"),
            ReasoningMessageContentEvent(message_id="r1", delta="why"),
            ToolCallArgsEvent(tool_call_id="t1", delta="1}"),
            TextMessageContentEvent(message_id="m1", delta="!"),
            ThinkingTextMessageContentEvent(delta="..."),
            ReasoningMessageContentEvent(message_id="r1", delta=" not"),
            text_end,
            tool_end,
            thinking_end,
            reasoning_end,
        ],
        log,
    )

    assert stored_events(log) == [
        dump_event(text_start),
        dump_event(tool_start),
        dump_event(TextMessageContentEvent(message_id="m1", delta="hi!")),
        dump_event(text_end),
        dump_event(ToolCallArgsEvent(tool_call_id="t1", delta='{"n":1}')),
        dump_event(tool_end),
        dump_event(ThinkingTextMessageContentEvent(delta="hmm...")),
        dump_event(thinking_end),
        dump_event(ReasoningMessageContentEvent(message_id="r1", delta="why not")),
        dump_event(reasoning_end),
    ]


async def test_a_truncated_stream_is_closed_so_replay_stays_valid(tmp_path: Path) -> None:
    """A client disconnect mid-message must not leave a content event without an end."""
    log = make_log(tmp_path)

    await forward_and_record(
        [
            TextMessageStartEvent(message_id="m1"),
            TextMessageContentEvent(message_id="m1", delta="hel"),
            TextMessageContentEvent(message_id="m1", delta="lo"),
            ToolCallStartEvent(tool_call_id="t1", tool_call_name="probe"),
            ToolCallArgsEvent(tool_call_id="t1", delta="{"),
        ],
        log,
    )

    assert stored_events(log) == [
        dump_event(TextMessageStartEvent(message_id="m1")),
        dump_event(ToolCallStartEvent(tool_call_id="t1", tool_call_name="probe")),
        dump_event(TextMessageContentEvent(message_id="m1", delta="hello")),
        dump_event(TextMessageEndEvent(message_id="m1")),
        dump_event(ToolCallArgsEvent(tool_call_id="t1", delta="{")),
        dump_event(ToolCallEndEvent(tool_call_id="t1")),
    ]


async def test_persist_ui_events_writes_without_a_stream(tmp_path: Path) -> None:
    log = make_log(tmp_path)
    event = CustomEvent(
        name="app.launched", value={"port": 8000, "path": "/", "label": "Preview", "url": "http://127.0.0.1:8000/"}
    )

    await persist_ui_events([event], log=log, run_id=RUN_ID)

    assert stored_events(log) == [dump_event(event)]
