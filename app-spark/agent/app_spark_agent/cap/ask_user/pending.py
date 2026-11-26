"""Inspect unanswered `ask_user_question` tool calls at the tail of a message history."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai_harness.ask_user import TOOL_NAME, AskUserRequest

logger = logging.getLogger(__name__)


class PendingAskUser:
    """View unanswered `ask_user_question` calls at the tail of a conversation's message history.

    Exposes two distinct output types over the same trailing history depending on caller needs:

    - :meth:`requests` (and :meth:`as_payloads`) -> ``list[PendingAskUserCall]`` containing
      schema-validated :class:`AskUserRequest` objects. Malformed historical tool arguments are
      logged and skipped instead of failing the caller. Use this for read-only external views
      such as ``GET /health``.
    - :meth:`tool_calls` -> ``list[ToolCallPart]`` containing the raw wire tool-call parts with
      no argument validation. Every unanswered call is preserved so protocol control paths --
      matching inbound ``toolCallId`` values or closing dangling calls when the user replies
      directly in chat -- never leave an unclosed tool call behind in model history.
    """

    def __init__(self, messages: Sequence[ModelMessage]) -> None:
        self._messages = messages

    def as_payloads(self) -> list[dict[str, object]]:
        """Serialize every valid pending request in snake_case for endpoints like `GET /health`."""
        return [item.as_payload() for item in self.requests()]

    def requests(self) -> list[PendingAskUserCall]:
        """Return schema-validated pending `AskUserRequest` items for read-only inspection.

        Unlike :meth:`tool_calls`, this parses each call's arguments via
        :meth:`AskUserRequest.from_tool_call` and skips malformed entries with a warning so a
        corrupted historical context cannot break `/health`.
        """
        pending: list[PendingAskUserCall] = []
        for call in self.tool_calls():
            try:
                request = AskUserRequest.from_tool_call(call)
            except (ValidationError, ValueError) as exc:
                logger.warning("skipping malformed pending ask_user_question call %s: %s", call.tool_call_id, exc)
                continue
            pending.append(PendingAskUserCall(tool_call=call, request=request))
        return pending

    def tool_calls(self) -> list[ToolCallPart]:
        """Return raw unanswered `ask_user_question` `ToolCallPart`s from the final model response.

        Unlike :meth:`requests`, this does not validate or filter tool arguments: callers that
        validate inbound answers or synthesize bypass tool-returns must see every dangling call
        ID so model history stays strictly balanced.

        A model response may contain sibling tools (e.g. `read_file` alongside `ask_user_question`).
        Those sibling tools execute during the pausing turn and leave a trailing `ModelRequest`
        with their `ToolReturnPart`s, so scanning from the last `ModelResponse` and subtracting
        any already-returned `tool_call_id`s handles both standalone and parallel-tool pauses.
        """
        last_response_index: int | None = None
        for index in range(len(self._messages) - 1, -1, -1):
            if isinstance(self._messages[index], ModelResponse):
                last_response_index = index
                break

        if last_response_index is None:
            return []

        resolved_ids: set[str] = set()
        for message in self._messages[last_response_index + 1 :]:
            if not isinstance(message, ModelRequest):
                continue
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    resolved_ids.add(part.tool_call_id)

        last_response = self._messages[last_response_index]
        assert isinstance(last_response, ModelResponse)
        return [
            part
            for part in last_response.parts
            if isinstance(part, ToolCallPart) and part.tool_name == TOOL_NAME and part.tool_call_id not in resolved_ids
        ]


@dataclass(frozen=True)
class PendingAskUserCall:
    """One schema-validated unanswered `ask_user_question` call paired with its original wire part."""

    tool_call: ToolCallPart
    request: AskUserRequest

    def as_payload(self) -> dict[str, object]:
        """Serialize in snake_case for Runtime responses such as `GET /health`."""
        return {
            "tool_call_id": self.request.id,
            "questions": [
                {
                    "header": question.header,
                    "question": question.question,
                    "options": [
                        {
                            "label": option.label,
                            "description": option.description,
                        }
                        for option in question.options
                    ],
                    "multi_select": question.multi_select,
                }
                for question in self.request.questions
            ],
        }
