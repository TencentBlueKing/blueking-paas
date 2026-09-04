"""Conversation context: validation, monotonic versioning, and atomic replacement."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai import ModelMessage
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from app_spark_agent.state import (
    STATE_SCHEMA_VERSION,
    ContextStore,
    ConversationContext,
    ConversationStateConflict,
    ConversationStateError,
)


def make_messages(conversation_id: str) -> list[ModelMessage]:
    run_id = str(uuid4())
    return [
        ModelRequest(
            parts=[UserPromptPart(content="hello")],
            run_id=run_id,
            conversation_id=conversation_id,
        ),
        ModelResponse(
            parts=[TextPart(content="world")],
            model_name="test-fixture",
            run_id=run_id,
            conversation_id=conversation_id,
        ),
    ]


def make_context(*, context_version: int = 1) -> ConversationContext:
    conversation_id = str(uuid4())
    return ConversationContext(
        conversation_id=conversation_id,
        context_version=context_version,
        messages=make_messages(conversation_id),
    )


async def test_context_round_trips_and_restores_idempotently(tmp_path: Path) -> None:
    path = tmp_path / "context.json"
    context = make_context()
    store = ContextStore(path)

    assert store.context.is_empty
    assert await store.restore(context) == context
    assert await store.restore(context) == context

    reloaded = ContextStore(path)
    assert reloaded.context == context
    assert json.loads(path.read_text())["schema_version"] == STATE_SCHEMA_VERSION


async def test_commit_advances_the_version_without_counting_runs(tmp_path: Path) -> None:
    """Compaction commits between model requests, so versions are not run boundaries."""
    store = ContextStore(tmp_path / "context.json")
    conversation_id = str(uuid4())
    messages = make_messages(conversation_id)

    assert (await store.commit(messages, conversation_id=conversation_id)).context_version == 1
    assert (await store.commit(messages, conversation_id=conversation_id)).context_version == 2
    assert (await store.commit(messages[:1], conversation_id=conversation_id)).context_version == 3
    assert store.context.messages == messages[:1]


async def test_restore_refuses_to_overwrite_an_active_context(tmp_path: Path) -> None:
    store = ContextStore(tmp_path / "context.json")
    conversation_id = str(uuid4())
    await store.commit(make_messages(conversation_id), conversation_id=conversation_id)

    with pytest.raises(ConversationStateConflict, match="cannot be overwritten"):
        await store.restore(make_context(context_version=9))


def test_a_summary_carrying_no_conversation_id_is_accepted() -> None:
    """Compaction synthesizes its summary outside any run, so it has no conversation id."""
    conversation_id = str(uuid4())
    summary = ModelRequest(parts=[SystemPromptPart(content="Summary of previous conversation:")])

    context = ConversationContext(
        conversation_id=conversation_id,
        context_version=4,
        messages=[summary, *make_messages(conversation_id)],
    )

    assert context.messages[0] is summary
    assert ConversationContext.from_payload(context.as_payload()) == context


def test_history_from_another_conversation_is_rejected() -> None:
    with pytest.raises(ConversationStateError, match="does not match the conversation"):
        ConversationContext(
            conversation_id=str(uuid4()),
            context_version=1,
            messages=make_messages(str(uuid4())),
        )


@pytest.mark.parametrize("conversation_id", ["", "   ", "\n\t"])
def test_a_blank_conversation_id_is_rejected(conversation_id: str) -> None:
    """Whitespace is not an identifier, so it is rejected rather than stored as one."""
    with pytest.raises(ValidationError):
        ConversationContext(conversation_id=conversation_id)


def test_a_padded_conversation_id_is_stored_stripped() -> None:
    """Normalizing here is what keeps the id comparable to the one carried by each message."""
    conversation_id = str(uuid4())
    context = ConversationContext(conversation_id=f"  {conversation_id}\n")

    assert context.conversation_id == conversation_id


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"schema_version": 1, "conversation_id": None, "context_version": 0, "messages": []},
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "conversation_id": None,
            "context_version": -1,
            "messages": [],
        },
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "conversation_id": 7,
            "context_version": 0,
            "messages": [],
        },
        {"schema_version": STATE_SCHEMA_VERSION, "conversation_id": None, "context_version": 0},
    ],
)
def test_an_invalid_payload_is_rejected(payload: object) -> None:
    """Every way a document can be wrong reaches the caller as one error type.

    The negative ``context_version`` is the case that matters: it passes the payload schema and
    is only caught when the context itself is built, which is inside the same translation.
    """
    with pytest.raises(ConversationStateError):
        ConversationContext.from_payload(payload)
