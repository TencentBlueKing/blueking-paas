"""GET /health: the single call a control plane polls the Runtime with.

Everything it reports is a cursor into something a client can fetch in full elsewhere, so the
interesting assertion is not the shape of the document but that its numbers agree with the
endpoints they point at.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app_spark_agent import VERSION, settings
from tests.api.support import HEALTH_FIELDS, RUNTIME_TOKEN, cold_context, drain_channel, run_turn


def test_an_empty_runtime_reports_no_conversation(api: TestClient) -> None:
    reported: dict[str, Any] = api.get("/health").json()

    assert reported["model"] == settings.MODEL
    assert reported["conversation_id"] is None
    assert reported["context_version"] == 0
    assert reported["log_seq"] == 0
    assert reported["ui_event_seq"] == 0
    assert set(reported) >= HEALTH_FIELDS
    assert reported["version"] == VERSION
    assert reported["model_ready"] is True
    assert reported["running"] is False
    assert reported["app_status"] == "not_started"


def test_every_reported_cursor_matches_the_endpoint_it_points_at(api: TestClient) -> None:
    conversation_id = str(uuid4())

    run_turn(api, conversation_id=conversation_id)

    reported: dict[str, Any] = api.get("/health").json()
    transcript = drain_channel(api, "/log")
    events = drain_channel(api, "/ui-events")
    context: dict[str, Any] = api.get("/context").json()

    assert reported["conversation_id"] == conversation_id
    assert reported["context_version"] == context["context_version"]
    assert reported["log_seq"] == transcript[-1]["seq"] == len(transcript)
    assert reported["ui_event_seq"] == events[-1]["seq"] == len(events)
    assert reported["running"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("MODEL_NAME", ""),
        ("MODEL_NAME", "not-a-listed-model"),
        ("MODEL_BASE_URL", ""),
    ],
)
def test_readiness_requires_url_and_listed_model(
    api: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    """网关地址和对照表内模型名缺一不可；表外名称不得假装就绪。"""
    monkeypatch.setattr(settings, field, value)

    reported: dict[str, Any] = api.get("/health").json()

    assert reported["model_ready"] is False


def test_a_missing_token_is_reported_as_unready(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """用户态 token 和兼容回落密钥都空，才算没有 access_token。"""
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)

    reported: dict[str, Any] = api.get("/health").json()

    assert reported["model_ready"] is False


def test_aidev_access_token_is_enough_when_the_api_key_is_absent(
    api: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户态 token 是正门；MODEL_API_KEY 只是兼容回落。"""
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", "user-access-token")

    reported: dict[str, Any] = api.get("/health").json()

    assert reported["model_ready"] is True


def test_a_fake_model_is_ready_without_an_api_key(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The deterministic fake model never calls a provider and therefore needs no credential."""
    monkeypatch.setattr(settings, "MODEL", "fake:write-file")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)

    reported: dict[str, Any] = api.get("/health").json()

    assert reported["model_ready"] is True


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Bearer "}, {"Authorization": "Bearer wrong"}, {"Authorization": "Bearer short"}],
)
def test_health_rejects_bad_token(api: TestClient, headers: dict[str, str] | None) -> None:
    # Skip AuthedTestClient so a missing token is not filled in.
    resp = TestClient(api.app).get("/health", headers=headers)
    assert resp.status_code == 401
    assert HEALTH_FIELDS.isdisjoint(resp.json())


def test_health_rejects_query_token(api: TestClient) -> None:
    """A query token is not an alternative to Bearer."""
    resp = TestClient(api.app).get("/health", params={"token": RUNTIME_TOKEN})
    assert resp.status_code == 401
    assert HEALTH_FIELDS.isdisjoint(resp.json())


def test_a_runtime_with_no_control_plane_says_so(api: TestClient) -> None:
    """The replication cursors are still reported, so one document answers "am I disposable"."""
    reported: dict[str, Any] = api.get("/health").json()

    assert reported["replicating"] is False
    assert reported["pushed_log_seq"] == 0
    assert reported["pushed_ui_event_seq"] == 0
    assert reported["pushed_context_version"] == 0
    # Not "nothing is pending" so much as "the question does not apply here": with no control
    # plane the state directory is the whole story, so it can never be behind one.
    assert reported["replication_pending"] is False


def test_a_restored_runtime_reports_the_history_it_inherited_as_replicated(
    api: TestClient,
) -> None:
    """Everything below the seeded base came from the control plane, so it is by definition
    already there -- reporting otherwise would make a fresh Runtime look permanently behind."""
    api.put("/context", params={"log_seq": 40, "ui_event_seq": 55}, json=cold_context())

    reported: dict[str, Any] = api.get("/health").json()

    assert reported["log_seq"] == 40
    assert reported["ui_event_seq"] == 55
    assert reported["pushed_log_seq"] == 40
    assert reported["pushed_ui_event_seq"] == 55
    assert reported["pushed_context_version"] == reported["context_version"]
