"""Idle clock on HTTP: reset only when a run ends; ``/health`` does not extend life."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app_spark_agent.server.lifecycle import IdleWatch
from app_spark_agent.server.runtime import ConversationRuntime
from tests.api.support import run_turn


def _idle(api: TestClient) -> IdleWatch:
    runtime = api.app.state.conversation_runtime
    assert isinstance(runtime, ConversationRuntime)
    return runtime.lifecycle.idle


def test_health_does_not_reset_idle_origin(api: TestClient) -> None:
    idle = _idle(api)
    origin = idle.last_idle_origin

    api.get("/health")
    api.get("/health")
    assert idle.last_idle_origin == origin

    run_turn(api, conversation_id=str(uuid4()))
    after_run = idle.last_idle_origin
    assert after_run > origin

    api.get("/health")
    assert idle.last_idle_origin == after_run
