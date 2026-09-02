"""Authoritative state is the AG-1 trio: failure is not persisted as success, and no messages.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic_ai_harness import ClearToolResults, TieredCompaction

from app_spark_agent.server.runtime import CONTEXT_FILENAME, TRANSCRIPT_FILENAME, UI_EVENTS_FILENAME
from tests.api.support import build_test_client, get_context, run_request, run_turn
from tests.support.fake_models import failing_model, probe, tool_then_fail_model

TINY_TARGET_TOKENS = 40
AUTHORITATIVE_FILES = {CONTEXT_FILENAME, TRANSCRIPT_FILENAME, UI_EVENTS_FILENAME}


def _state_dir(client: TestClient) -> Path:
    runtime = client.app.state.conversation_runtime
    return runtime.context_store.path.parent


def test_successful_run_writes_three_files_and_not_messages_json(api: TestClient) -> None:
    run_turn(api, conversation_id=str(uuid4()))

    state_dir = _state_dir(api)
    names = {path.name for path in state_dir.iterdir() if path.is_file()}
    assert names >= AUTHORITATIVE_FILES
    assert "messages.json" not in names
    context: dict[str, Any] = api.get("/context").json()
    assert context["context_version"] == 1
    assert context["messages"]


def test_failed_run_does_not_commit_as_successful(tmp_path: Path) -> None:
    client = build_test_client(tmp_path, model=failing_model())

    with client:
        response = run_request(client, conversation_id=str(uuid4()), context_version=0)
        context = get_context(client)
        state_dir = _state_dir(client)

    assert context["context_version"] == 0
    assert context["messages"] == []
    assert not (state_dir / "messages.json").exists()
    # Failure may be 200 + RUN_ERROR or a non-200; what matters is no successful end state.
    if response.status_code == 200:
        assert "RUN_FINISHED" not in response.text


def test_mid_run_compaction_may_remain_when_the_run_then_fails(tmp_path: Path) -> None:
    client = build_test_client(
        tmp_path,
        model=tool_then_fail_model(tool_rounds=3),
        tools=[probe],
        capabilities=[
            TieredCompaction[object](
                tiers=[ClearToolResults[object](max_tokens=1, keep_pairs=1)],
                target_tokens=TINY_TARGET_TOKENS,
            )
        ],
    )

    with client:
        response = run_request(client, conversation_id=str(uuid4()), context_version=0)
        context = get_context(client)

    assert context["context_version"] >= 1
    assert context["messages"]
    if response.status_code == 200:
        assert "RUN_FINISHED" not in response.text
    # Mid-run compaction may remain after failure; the turn must not be written as a successful end.
    kinds = [message.get("kind") for message in cast(list[dict[str, Any]], context["messages"])]
    assert "response" in kinds
