"""Prepare a run's opening message history, transcript entries, and opening UI events.

Separates the three distinct ways a turn can begin so :mod:`app_spark_agent.server.routes` stays
a thin HTTP view layer:

1. **Ordinary user message (no pending `ask_user_question`)** -- the common path: prior history
   is passed unchanged, the new user turn is pre-recorded into ``log.jsonl``, and no extra UI
   events are injected.
2. **User message bypassing pending `ask_user_question` call(s)** -- only entered when the tail
   of prior history actually holds unanswered `ask_user_question` calls: closes them with a
   synthetic ``ToolReturnPart`` *before* the new user message (preserving the strict
   ``assistant(tool_calls) -> tool -> user`` order required by OpenAI-compatible providers),
   records both into ``log.jsonl``, and emits matching ``TOOL_CALL_RESULT`` UI events.
3. **Structured answer to pending `ask_user_question` call(s)** -- ``deferred_tool_results`` is
   present and there is no new user message to pre-record; hands the prior history length to
   :class:`TranscriptRecorder` so it captures the framework-synthesized ``ToolReturnPart`` on
   the first model request.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ag_ui.core import BaseEvent
from pydantic_ai.messages import ModelMessage

from app_spark_agent.cap.ask_user import (
    PendingAskUser,
    build_bypass_message,
    build_bypass_ui_events,
)
from app_spark_agent.recorder import record_messages
from app_spark_agent.server.run_input import PreparedRun
from app_spark_agent.state import AppendLog


@dataclass(frozen=True)
class RunOpening:
    """Opening state handed to ``AGUIAdapter.run_stream`` and ``TranscriptRecorder``."""

    message_history: list[ModelMessage]
    # Set only for deferred-resume runs so `TranscriptRecorder` captures the opening tool returns.
    initial_message_count: int | None = None
    # Extra AG-UI events to emit right after `RUN_STARTED` (empty on ordinary turns).
    opening_ui_events: tuple[BaseEvent, ...] = ()


async def prepare_run_opening(
    *,
    prepared: PreparedRun,
    prior_messages: Sequence[ModelMessage],
    user_turn_messages: Sequence[ModelMessage],
    transcript: AppendLog,
) -> RunOpening:
    """Prepare opening history and persist opening transcript records for one inbound run.

    :param prepared: Validated request metadata from :func:`prepare_run`.
    :param prior_messages: Committed context messages before this run starts.
    :param user_turn_messages: Sanitized client messages for a normal user turn (empty when
        answering pending questions).
    :param transcript: Append-only raw transcript channel (``log.jsonl``).
    :return: The history, recorder hint, and optional opening UI events for the run.
    """
    if prepared.deferred_tool_results is not None:
        return _open_deferred_answer_run(prior_messages)

    return await _open_user_message_run(
        prepared=prepared,
        prior_messages=prior_messages,
        user_turn_messages=user_turn_messages,
        transcript=transcript,
    )


def _open_deferred_answer_run(prior_messages: Sequence[ModelMessage]) -> RunOpening:
    """Prepare a run that resumes paused `ask_user_question` call(s) via `deferred_tool_results`.

    Nothing is written to ``transcript`` up front: ``CallToolsNode`` synthesizes the real
    ``ModelRequest(ToolReturnPart)`` before the first ``before_model_request``, and passing
    ``initial_message_count=len(history)`` lets ``TranscriptRecorder`` capture that suffix.
    """
    history = list(prior_messages)
    return RunOpening(
        message_history=history,
        initial_message_count=len(history),
    )


async def _open_user_message_run(
    *,
    prepared: PreparedRun,
    prior_messages: Sequence[ModelMessage],
    user_turn_messages: Sequence[ModelMessage],
    transcript: AppendLog,
) -> RunOpening:
    """Prepare a normal user-message run, closing pending `ask_user_question` calls only if present."""
    history = list(prior_messages)
    pending_calls = PendingAskUser(history).tool_calls()

    if not pending_calls:
        # Common path: no pending question to close, just record the new user turn.
        # Recorded here rather than inferred from the run's history: the framework merges this
        # turn into a restored trailing request before any capability sees it, and the adapter
        # is the only place that still knows the turn on its own.
        await record_messages(transcript, prepared.run_id, user_turn_messages)
        return RunOpening(message_history=history)

    # Bypass path: the user ignored the pending question card and chatted directly. Close every
    # dangling ask_user_question before the new user message so OpenAI-compatible providers see
    # `assistant(tool_calls) -> tool -> user`, and emit matching TOOL_CALL_RESULT UI events.
    bypass_message = build_bypass_message(
        pending_calls,
        conversation_id=prepared.conversation_id,
    )
    history.append(bypass_message)
    await record_messages(transcript, prepared.run_id, [bypass_message, *user_turn_messages])
    return RunOpening(
        message_history=history,
        opening_ui_events=tuple(build_bypass_ui_events(pending_calls)),
    )
