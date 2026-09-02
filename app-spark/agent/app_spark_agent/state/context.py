"""The mutable conversation context: the history actually sent to the model."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)
from pydantic_ai import ModelMessage

from app_spark_agent.utils import write_atomic

# Annotated so a bump that forgets one of the two halves fails type checking rather than
# silently accepting documents the payload model no longer describes.
SchemaVersion = Literal[3]
STATE_SCHEMA_VERSION: SchemaVersion = 3

# Surrounding whitespace is stripped rather than rejected, so the id a caller sent and the id
# the Runtime stores can never differ by invisible characters; what remains has to be non-empty.
ConversationId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ConversationStateError(RuntimeError):
    """Raised when persisted conversation state is invalid or cannot be replaced."""


class ConversationStateConflict(ConversationStateError):
    """Raised when a cold context would overwrite an active Runtime state."""


class ConversationContext(BaseModel):
    """The trusted model history for one revision of a conversation.

    ``context_version`` deliberately does not count runs. Compaction fires inside a run, between
    model requests, so the context can change without a run boundary and a run can finish having
    changed it more than once. The version only promises to move forward on every commit.

    This is the in-memory shape; :class:`ContextPayload` is the document it is stored and
    transferred as.
    """

    model_config = ConfigDict(frozen=True)

    conversation_id: ConversationId | None = None
    context_version: int = Field(default=0, ge=0)
    messages: list[ModelMessage] = Field(default_factory=list[ModelMessage])

    @model_validator(mode="after")
    def _check_messages_belong_here(self) -> Self:
        """Check the one thing the field constraints cannot: that the history is this history."""
        if self.messages and self.conversation_id is None:
            raise ConversationStateError("conversation_id is required when messages are present")

        # A compaction summary is synthesized outside any run, so it carries no conversation_id
        # at all; only a mismatched one indicates foreign history.
        if any(
            message.conversation_id is not None and message.conversation_id != self.conversation_id
            for message in self.messages
        ):
            raise ConversationStateError("message conversation_id does not match the conversation")
        return self

    @property
    def is_empty(self) -> bool:
        """Return whether this context represents a new conversation."""
        return self.conversation_id is None and self.context_version == 0 and not self.messages

    def as_payload(self) -> dict[str, object]:
        """Return the versioned JSON-compatible context representation."""
        return ContextPayload.of(self).model_dump(mode="json")

    def as_document(self) -> bytes:
        """Return the versioned context serialized exactly as it is written to disk."""
        return ContextPayload.of(self).model_dump_json().encode()

    @classmethod
    def from_payload(cls, raw: object) -> ConversationContext:
        """Validate and structure a JSON-compatible context representation.

        The structuring is inside the ``try`` because it validates too: a document can be a
        well-formed payload and still describe an impossible context, such as a negative
        version. Either way the caller sees one error type.
        """
        try:
            return ContextPayload.model_validate(raw).to_context()
        except ValidationError as exc:
            raise ConversationStateError(f"invalid context payload: {exc}") from exc

    @classmethod
    def from_document(cls, raw: bytes) -> ConversationContext:
        """Validate and structure a serialized context document."""
        try:
            return ContextPayload.model_validate_json(raw).to_context()
        except ValidationError as exc:
            raise ConversationStateError(f"invalid context payload: {exc}") from exc


class ContextPayload(BaseModel):
    """The versioned document a context is persisted and transferred as.

    Split from :class:`ConversationContext` because the two answer different questions: this one
    describes what a stored document must contain, starting with the ``schema_version`` that
    says whether it can be read at all, while the context itself only carries the state the
    Runtime works with. Rejecting an unreadable document is therefore pure schema validation.

    The stored keys are the field names, so nothing is renamed on the way to disk or back.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion
    conversation_id: str | None
    context_version: int
    messages: list[ModelMessage]

    @classmethod
    def of(cls, context: ConversationContext) -> ContextPayload:
        """Return the document representing ``context`` under the current schema version."""
        return cls(
            schema_version=STATE_SCHEMA_VERSION,
            conversation_id=context.conversation_id,
            context_version=context.context_version,
            messages=context.messages,
        )

    def to_context(self) -> ConversationContext:
        """Return the context this document describes, applying its own invariants."""
        return ConversationContext(
            conversation_id=self.conversation_id,
            context_version=self.context_version,
            messages=self.messages,
        )


class ContextStore:
    """Atomically replace the conversation context owned by one Runtime process.

    The context is the only artifact a cold start may be rebuilt from. It must never be derived
    by concatenating the raw transcript: ``SummarizingCompaction`` replaces history with an LLM
    call, which is neither replayable nor deterministic, so a rebuilt context would differ from
    the one the model was actually given.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._context = self._load()

    @property
    def context(self) -> ConversationContext:
        """Return the last fully committed context."""
        return self._context

    async def commit(
        self,
        messages: Sequence[ModelMessage],
        *,
        conversation_id: str,
    ) -> ConversationContext:
        """Replace the context with ``messages`` under the next version and return it."""
        async with self._lock:
            updated = ConversationContext(
                conversation_id=conversation_id,
                context_version=self._context.context_version + 1,
                messages=list(messages),
            )
            await self._persist(updated)
            return updated

    async def restore(self, context: ConversationContext) -> ConversationContext:
        """Initialize an empty store from a cold context, idempotently."""
        async with self._lock:
            current = self._context
            if current == context:
                return current
            if not current.is_empty:
                raise ConversationStateConflict("an active conversation context cannot be overwritten")
            await self._persist(context)
            return context

    async def _persist(self, context: ConversationContext) -> None:
        await asyncio.to_thread(write_atomic, self.path, context.as_document())
        self._context = context

    def _load(self) -> ConversationContext:
        if not self.path.exists():
            return ConversationContext()
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise ConversationStateError(f"unable to read conversation context: {exc}") from exc
        return ConversationContext.from_document(raw)
