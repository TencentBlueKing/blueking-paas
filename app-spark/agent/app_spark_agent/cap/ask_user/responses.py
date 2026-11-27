"""Validate inbound `forwardedProps.askUserResponses` and build `DeferredToolResults`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from pydantic_ai import DeferredToolResults
from pydantic_ai.messages import ToolCallPart
from pydantic_ai_harness.ask_user import (
    AskUserAnswer,
    AskUserRequest,
    AskUserResponse,
    ask_user_result,
)

from app_spark_agent.utils import first_validation_error


class AskUserValidationError(ValueError):
    """The caller's answer payload is malformed or does not fit the pending question schema (HTTP 422)."""


class AskUserConflictError(ValueError):
    """The conversation is no longer waiting on the referenced question call (HTTP 409)."""


def build_ask_user_deferred_results(
    raw_responses: object,
    pending_calls: Sequence[ToolCallPart],
) -> DeferredToolResults:
    """Validate `forwardedProps.askUserResponses` against `pending_calls` and build `DeferredToolResults`.

    :param raw_responses: Raw value of `forwardedProps.askUserResponses`.
    :param pending_calls: Unanswered `ask_user_question` tool calls currently at the tail of context.
    :return: Ready-to-run `DeferredToolResults` mapping every pending tool call ID to its result.
    :raises AskUserValidationError: On schema, completeness, or option/answer validation errors (422).
    :raises AskUserConflictError: When no questions are pending or an unknown toolCallId is supplied (409).
    """
    parsed = _parse_responses(raw_responses)
    seen_ids = _require_unique_tool_call_ids(parsed)

    if not pending_calls:
        raise AskUserConflictError("There are no pending questions to answer.")

    pending_by_id = {call.tool_call_id: call for call in pending_calls}
    unexpected = [item.tool_call_id for item in parsed if item.tool_call_id not in pending_by_id]
    if unexpected:
        raise AskUserConflictError(f"Question tool call(s) are not pending: {', '.join(unexpected)}.")

    missing = [call.tool_call_id for call in pending_calls if call.tool_call_id not in seen_ids]
    if missing:
        raise AskUserValidationError(f"Missing responses for pending question tool call(s): {', '.join(missing)}.")

    results: dict[str, Any] = {}
    for item in parsed:
        call = pending_by_id[item.tool_call_id]
        results[call.tool_call_id] = _build_single_result(call, item)

    return DeferredToolResults(calls=results)


def _parse_responses(raw_responses: object) -> list[_ResponseInput]:
    try:
        parsed = _RESPONSES_ADAPTER.validate_python(raw_responses)
    except ValidationError as exc:
        raise AskUserValidationError(
            f"Invalid forwardedProps.askUserResponses: {first_validation_error(exc)}"
        ) from exc

    if not parsed:
        raise AskUserValidationError("forwardedProps.askUserResponses must contain at least one response.")
    return parsed


def _require_unique_tool_call_ids(parsed: Sequence[_ResponseInput]) -> set[str]:
    seen_ids: set[str] = set()
    for item in parsed:
        if item.tool_call_id in seen_ids:
            raise AskUserValidationError(
                f"Duplicate toolCallId in forwardedProps.askUserResponses: {item.tool_call_id!r}."
            )
        seen_ids.add(item.tool_call_id)
    return seen_ids


def _build_single_result(call: ToolCallPart, item: _ResponseInput) -> Any:
    try:
        request = AskUserRequest.from_tool_call(call)
    except (ValidationError, ValueError) as exc:
        raise AskUserValidationError(f"Stored question {call.tool_call_id!r} is invalid: {exc}") from exc

    response = AskUserResponse(
        answers=tuple(
            AskUserAnswer(
                header=answer.header,
                selected=tuple(answer.selected),
                custom_answer=answer.custom_answer,
            )
            for answer in item.answers
        ),
        cancelled=item.cancelled,
    )
    try:
        return ask_user_result(request, response)
    except ValueError as exc:
        raise AskUserValidationError(str(exc)) from exc


class _AnswerInput(BaseModel):
    """Strict wire schema for one answered question inside `forwardedProps.askUserResponses`."""

    # `extra="forbid"` rejects unsupported Phase-1 fields like `note` or typos instead of dropping them.
    # `strict=True` stops booleans/ints from being silently coerced into strings or lists.
    model_config = ConfigDict(extra="forbid", strict=True)

    header: str
    selected: list[str] = Field(default_factory=list)
    custom_answer: str | None = Field(default=None, alias="customAnswer")


class _ResponseInput(BaseModel):
    """Strict wire schema for one tool call response inside `forwardedProps.askUserResponses`."""

    model_config = ConfigDict(extra="forbid", strict=True)

    tool_call_id: str = Field(alias="toolCallId", min_length=1)
    answers: list[_AnswerInput] = Field(default_factory=list[_AnswerInput])
    cancelled: bool = False


_RESPONSES_ADAPTER = TypeAdapter(list[_ResponseInput])
