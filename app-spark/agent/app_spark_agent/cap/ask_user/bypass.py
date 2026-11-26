"""Close pending `ask_user_question` calls when the user replies directly in chat instead."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from ag_ui.core import ToolCallResultEvent
from pydantic_ai.messages import ModelRequest, ToolCallPart, ToolReturnPart

# Returned as the tool result when a user ignores a pending question card and sends a normal chat
# message instead. Distinct from `DECLINED` so both the model and the UI can tell "user clicked
# Skip" apart from "user replied directly in chat".
BYPASSED_BY_USER_MESSAGE = (
    "The user did not answer the question directly and sent a new message instead. Follow the user's new message."
)


def build_bypass_message(
    pending_calls: Sequence[ToolCallPart],
    *,
    conversation_id: str,
) -> ModelRequest:
    """Build a `ModelRequest` closing every pending `ask_user_question` call before a new user message.

    OpenAI-compatible providers require tool results to immediately follow the assistant message
    that issued the tool calls, before any subsequent user message. Appending this message to the
    prior history keeps the message order valid for every model provider.

    Deliberately leaves `run_id=None`: pydantic-ai rejects a `run_id` that already appears on
    `message_history`, and `log.jsonl` already attributes the entry to the new run in its envelope.
    """
    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name=call.tool_name,
                content=BYPASSED_BY_USER_MESSAGE,
                tool_call_id=call.tool_call_id,
            )
            for call in pending_calls
        ],
        conversation_id=conversation_id,
    )


def build_bypass_ui_events(pending_calls: Sequence[ToolCallPart]) -> list[ToolCallResultEvent]:
    """Build AG-UI `TOOL_CALL_RESULT` events closing bypassed questions on the wire and event log."""
    return [
        ToolCallResultEvent(
            message_id=str(uuid4()),
            tool_call_id=call.tool_call_id,
            content=BYPASSED_BY_USER_MESSAGE,
            role="tool",
        )
        for call in pending_calls
    ]
