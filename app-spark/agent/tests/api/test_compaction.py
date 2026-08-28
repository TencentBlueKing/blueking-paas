"""Compaction must never reach the raw transcript, only the context."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic_ai_harness import ClearToolResults, SummarizingCompaction, TieredCompaction

from tests.api.support import (
    build_test_client,
    get_context,
    get_transcript_messages,
    run_request,
)
from tests.support.fake_models import probe, summarizing_model, tool_calling_model

# Low enough that the tiers run on every request after the first tool result lands.
TINY_TARGET_TOKENS = 40

CLEARED = "[tool result cleared]"
SUMMARY_PREFIX = "Summary of previous conversation:"


def clearing_client(tmp_path: Path, *, rounds: int) -> TestClient:
    return build_test_client(
        tmp_path,
        model=tool_calling_model(rounds),
        tools=[probe],
        capabilities=[
            TieredCompaction[object](
                tiers=[ClearToolResults[object](max_tokens=1, keep_pairs=1)],
                target_tokens=TINY_TARGET_TOKENS,
            )
        ],
    )


def test_mid_run_compaction_does_not_reach_the_raw_transcript(tmp_path: Path) -> None:
    """The core guarantee: a run whose own tool results get blanked still logs the originals.

    ``ClearToolResults`` rewrites history in ``before_model_request``, and that rewrite is
    written back into the run's message history. Everything derived at run end -- including
    ``all_messages()`` and ``new_messages()`` -- therefore sees the blanked results, so the
    transcript can only be correct if it was captured while each message was still intact.
    """
    rounds = 3
    client = clearing_client(tmp_path, rounds=rounds)

    with client:
        response = run_request(client, conversation_id=str(uuid4()), context_version=0)
        assert response.status_code == 200, response.text

        logged = _tool_return_contents(get_transcript_messages(client))
        stored = _tool_return_contents(get_context(client)["messages"])

    assert len(logged) == rounds
    assert all(
        content.startswith(f"probe-payload-{index}-") for index, content in enumerate(logged)
    )

    # The context kept only the most recent pair intact, which is exactly the content the
    # transcript would have lost had it been derived from the run result.
    assert stored == [CLEARED, CLEARED, logged[-1]]


def test_compaction_advances_the_context_version_inside_a_run(tmp_path: Path) -> None:
    """A compaction that fires mid-run is persisted immediately, not deferred to the run end."""
    client = clearing_client(tmp_path, rounds=3)

    with client:
        assert (
            run_request(client, conversation_id=str(uuid4()), context_version=0).status_code == 200
        )
        health: dict[str, Any] = client.get("/health").json()
        persisted_version = get_context(client)["context_version"]

    # One commit per compacting request plus the end-of-run commit, so a single run moves the
    # version by more than one. Runs and context versions are deliberately not in step.
    assert health["context_version"] > 1
    assert persisted_version == health["context_version"]


def test_summary_enters_the_context_but_never_the_transcript(tmp_path: Path) -> None:
    """A summary is synthesized by compaction, so it is context -- it is not conversation."""
    client = build_test_client(
        tmp_path,
        model=tool_calling_model(3),
        tools=[probe],
        capabilities=[
            TieredCompaction[object](
                tiers=[
                    SummarizingCompaction[object](
                        model=summarizing_model("the agent probed three times"),
                        max_messages=1,
                        keep_messages=2,
                    )
                ],
                target_tokens=TINY_TARGET_TOKENS,
            )
        ],
    )

    with client:
        assert (
            run_request(client, conversation_id=str(uuid4()), context_version=0).status_code == 200
        )

        context_messages = get_context(client)["messages"]
        transcript_messages = get_transcript_messages(client)

    context_text = _all_part_content(context_messages)
    transcript_text = _all_part_content(transcript_messages)

    assert any(text.startswith(SUMMARY_PREFIX) for text in context_text)
    assert not any(text.startswith(SUMMARY_PREFIX) for text in transcript_text)
    # The summary replaced the prefix it covers, so the context is now strictly smaller than
    # the conversation the transcript recorded.
    assert len(context_messages) < len(transcript_messages)


def test_replay_detection_survives_compaction_dropping_the_run(tmp_path: Path) -> None:
    """A committed runId stays rejected even once compaction forgot the run ever happened."""
    client = build_test_client(
        tmp_path,
        model=tool_calling_model(2),
        tools=[probe],
        capabilities=[
            TieredCompaction[object](
                tiers=[
                    SummarizingCompaction[object](
                        model=summarizing_model("earlier work"),
                        max_messages=1,
                        keep_messages=1,
                    )
                ],
                target_tokens=TINY_TARGET_TOKENS,
            )
        ],
    )
    conversation_id = str(uuid4())
    first_run_id = str(uuid4())

    with client:
        first = run_request(
            client,
            conversation_id=conversation_id,
            context_version=0,
            run_id=first_run_id,
        )
        assert first.status_code == 200, first.text

        version: int = client.get("/health").json()["context_version"]
        assert (
            run_request(
                client, conversation_id=conversation_id, context_version=version
            ).status_code
            == 200
        )

        current: int = client.get("/health").json()["context_version"]
        replay = run_request(
            client, conversation_id=conversation_id, context_version=current, run_id=first_run_id
        )
        context_messages = get_context(client)["messages"]

    context_run_ids = {message.get("run_id") for message in context_messages}
    assert first_run_id not in context_run_ids, "the test needs compaction to drop the first run"
    assert replay.status_code == 409
    assert "already been committed" in replay.json()["detail"]


def _all_part_content(messages: list[dict[str, Any]]) -> list[str]:
    return [
        part["content"]
        for message in messages
        for part in message.get("parts", [])
        if isinstance(part.get("content"), str)
    ]


def _tool_return_contents(messages: list[dict[str, Any]]) -> list[str]:
    """Return the content of every tool result in a serialized message list."""
    return [
        part["content"]
        for message in messages
        for part in message.get("parts", [])
        if part.get("part_kind") == "tool-return"
    ]
