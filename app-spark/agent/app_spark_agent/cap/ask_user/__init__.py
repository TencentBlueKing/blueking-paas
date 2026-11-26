"""Pending `ask_user_question` inspection, response validation, and chat-bypass closure.

The agent configures `AskUser(answerer=None)` so every clarifying question pauses the run cleanly
with `DeferredToolRequests` instead of holding an in-process future open across an idle sandbox.
Pending questions therefore have no side-channel state: they are derived directly from the
unanswered `ask_user_question` tool calls at the tail of `context.messages`.
"""

from app_spark_agent.cap.ask_user.bypass import (
    BYPASSED_BY_USER_MESSAGE,
    build_bypass_message,
    build_bypass_ui_events,
)
from app_spark_agent.cap.ask_user.pending import PendingAskUser, PendingAskUserCall
from app_spark_agent.cap.ask_user.responses import (
    AskUserConflictError,
    AskUserValidationError,
    build_ask_user_deferred_results,
)

__all__ = [
    "BYPASSED_BY_USER_MESSAGE",
    "AskUserConflictError",
    "AskUserValidationError",
    "PendingAskUser",
    "PendingAskUserCall",
    "build_ask_user_deferred_results",
    "build_bypass_message",
    "build_bypass_ui_events",
]
