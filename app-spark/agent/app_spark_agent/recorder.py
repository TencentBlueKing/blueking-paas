"""Capture the raw model transcript before compaction can rewrite it."""

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
    """Capture raw messages before compaction and commit context on mid-run compaction.

    Ordered ``outermost`` and reads ``ctx.messages`` (persistent history) rather than
    ``request_context.messages`` (an ephemeral outgoing view that ``Model.prepare_messages`` or
    request-only hooks may copy without mutating history). The caller records the opening user
    turn before the run starts; set ``initial_message_count`` for deferred-resume runs instead.
    """

    def __init__(
        self,
        *,
        log: AppendLog,
        context_store: ContextStore,
        conversation_id: str,
        run_id: str,
        initial_message_count: int | None = None,
    ) -> None:
        self._log = log
        self._context_store = context_store
        self._conversation_id = conversation_id
        self._run_id = run_id
        self._initial_message_count = initial_message_count
        # Strong refs to recorded messages so id() comparison stays sound (prevents address reuse).
        self._settled: list[ModelMessage] | None = None
        self._sent: list[ModelMessage] | None = None
        self._compactions = 0

    @property
    def compactions(self) -> int:
        """Number of mid-run context commits triggered by compaction."""
        return self._compactions

    def get_ordering(self) -> CapabilityOrdering:
        """Pin outermost so hooks wrap every compaction capability."""
        return CapabilityOrdering(position="outermost")

    async def before_model_request(
        self,
        ctx: RunContext[Any],
        request_context: ModelRequestContext,
    ) -> ModelRequestContext:
        """Record newly appended messages before inner capabilities can compact ``ctx.messages``."""
        messages = ctx.messages
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
        """Record the raw response and commit ``ctx.messages`` if compaction rewrote it."""
        settled = list(ctx.messages)
        if self._was_compacted(settled):
            self._compactions += 1
            # Commit immediately so a later crash does not re-pay summarizing compaction.
            await self._context_store.commit(settled, conversation_id=self._conversation_id)
        await self._record([response])
        settled.append(response)
        self._settled = settled
        return response

    async def flush_trailing(self, messages: Sequence[ModelMessage]) -> None:
        """Record trailing tool-return messages produced right before a deferred pause."""
        trailing = self._unrecorded(messages)
        if not trailing:
            return
        await self._record(trailing)
        if self._settled is not None:
            self._settled = [*self._settled, *trailing]

    def _unrecorded(self, messages: Sequence[ModelMessage]) -> list[ModelMessage]:
        """Return the trailing suffix appended since the previous request settled.

        Scanning backward skips compaction summaries spliced in at the head.
        """
        if self._settled is None:
            # First request: deferred-resume runs slice past prior history; normal runs already
            # recorded their opening user turn before starting.
            if self._initial_message_count is not None:
                return list(messages[self._initial_message_count :])
            return []

        recorded = {id(message) for message in self._settled}
        appended = 0
        for message in reversed(messages):
            if id(message) in recorded:
                break
            appended += 1
        return list(messages[len(messages) - appended :]) if appended else []

    def _was_compacted(self, settled: Sequence[ModelMessage]) -> bool:
        """Return whether persistent history was replaced or resized during this request step."""
        sent = self._sent
        if sent is None:
            return False
        if len(settled) != len(sent):
            return True
        return any(after is not before for after, before in zip(settled, sent, strict=True))

    async def _record(self, messages: Sequence[ModelMessage]) -> None:
        await record_messages(self._log, self._run_id, messages)
