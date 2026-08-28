"""Capture the raw model transcript before compaction can rewrite it."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.capabilities import AbstractCapability, CapabilityOrdering
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import RunContext

from app_spark_agent.state import AppendLog, ContextStore


async def record_messages(
    log: AppendLog,
    run_id: str,
    messages: Sequence[ModelMessage],
) -> None:
    """Append ``messages`` to the raw transcript exactly as they stand.

    :param log: Append-only channel receiving the serialized model messages.
    :param run_id: Run the recorded entries are attributed to.
    :param messages: Messages to persist; an empty sequence is a no-op.
    """
    if not messages:
        return
    payloads = json.loads(ModelMessagesTypeAdapter.dump_json(list(messages)))
    await log.append(run_id, payloads)


class TranscriptRecorder(AbstractCapability[Any]):
    """Record the raw transcript and keep the durable context in step with compaction.

    Compaction runs in ``before_model_request`` and its result is written back into the run's
    message history, so ``AgentRunResult.all_messages()`` and ``new_messages()`` both return the
    *compacted* transcript. That includes rewrites of messages the current run just produced: a
    run with many tool calls will have its own early tool results blanked by ``ClearToolResults``
    long before it finishes. Copying the transcript out at run end therefore loses content, and
    the only correct place to capture a message is while it is still untouched.

    This capability is ordered outermost so ``before_model_request`` observes the history before
    any other capability edits it, and its ``after_model_request`` observes the settled history
    after every other capability has run.

    The run's opening state -- the prior context plus the new user turn -- is recorded by the
    caller before the run starts, so this capability records nothing on the first request.

    :param log: Append-only channel receiving the raw model messages.
    :param context_store: Store committed whenever compaction changes the context mid-run.
    :param conversation_id: Conversation this run belongs to.
    :param run_id: Run the recorded entries are attributed to.
    """

    def __init__(
        self,
        *,
        log: AppendLog,
        context_store: ContextStore,
        conversation_id: str,
        run_id: str,
    ) -> None:
        self._log = log
        self._context_store = context_store
        self._conversation_id = conversation_id
        self._run_id = run_id
        # Messages already recorded, held by strong reference so identity comparison against a
        # later history stays sound: a dropped message must not have its address reused by a
        # genuinely new one.
        self._settled: list[ModelMessage] | None = None
        self._sent: list[ModelMessage] | None = None
        self._compactions = 0

    @property
    def compactions(self) -> int:
        """Return how many model requests were preceded by a context-changing compaction.

        :return: Count of mid-run context commits triggered by this capability.
        """
        return self._compactions

    def get_ordering(self) -> CapabilityOrdering:
        """Place this capability outermost so it sees the history before any other edits it.

        :return: Ordering that pins this capability to the outside of the stack.
        """
        return CapabilityOrdering(position="outermost")

    async def before_model_request(
        self,
        ctx: RunContext[Any],
        request_context: ModelRequestContext,
    ) -> ModelRequestContext:
        """Record everything appended since the last request, before compaction can rewrite it.

        :param ctx: Current run context from the capability protocol.
        :param request_context: Incoming request whose ``messages`` are the current history.
        :return: ``request_context`` unchanged.
        """
        messages = request_context.messages
        await self._record(self._unrecorded(messages))
        self._sent = list(messages)
        return request_context

    async def after_model_request(
        self,
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        """Record the raw response and persist the context when compaction changed it.

        :param ctx: Current run context from the capability protocol.
        :param request_context: Request after inner capabilities have run, including compaction.
        :param response: Raw model response, still untouched by later compaction.
        :return: ``response`` unchanged.
        """
        settled = list(request_context.messages)
        if self._was_compacted(settled):
            self._compactions += 1
            # Persist immediately rather than at run end: a summarizing tier costs a model call,
            # and a crash before the run boundary would otherwise resume from the uncompacted
            # context and pay for that call a second time. The cost is that a run which then
            # fails leaves a mid-run context, ending on the request the model never answered --
            # a valid history to continue from, and cheaper than re-summarizing.
            await self._context_store.commit(settled, conversation_id=self._conversation_id)
        await self._record([response])
        settled.append(response)
        self._settled = settled
        return response

    def _unrecorded(self, messages: Sequence[ModelMessage]) -> list[ModelMessage]:
        """Return the messages appended since the previous request settled.

        Nothing but appends happen between one request settling and the next one starting --
        compaction only runs inside ``before_model_request``, which this capability precedes --
        so the new messages are always a suffix. Scanning back from the end rather than taking a
        set difference is what keeps a compaction artifact out of the transcript: a summary is
        an unrecognized message too, but it is spliced in at the *head*, and every tier leaves
        the recent tail alone, so the scan stops long before reaching it.
        """
        if self._settled is None:
            # First request of the run: the caller already recorded the prior context and the
            # user turn. Nothing here can be diffed anyway, because the framework rebuilds these
            # messages before this hook runs -- history cleanup merges the new user turn into a
            # restored trailing request, so neither identity nor length identifies what is new.
            return []

        recorded = {id(message) for message in self._settled}
        appended = 0
        for message in reversed(messages):
            if id(message) in recorded:
                break
            appended += 1
        return list(messages[len(messages) - appended :]) if appended else []

    def _was_compacted(self, settled: Sequence[ModelMessage]) -> bool:
        """Return whether a capability rewrote the history this request was built from.

        Compaction hands back a fresh list whose rewritten entries are new objects, so an
        element-wise identity comparison against what this capability saw on the way in
        distinguishes a compacted history from an untouched one.
        """
        sent = self._sent
        if sent is None:
            return False
        if len(settled) != len(sent):
            return True
        return any(after is not before for after, before in zip(settled, sent, strict=True))

    async def _record(self, messages: Sequence[ModelMessage]) -> None:
        await record_messages(self._log, self._run_id, messages)
