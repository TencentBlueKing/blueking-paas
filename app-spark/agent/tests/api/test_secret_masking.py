"""Credentials must not leave the process through anything a caller or an auditor reads.

Here: HTTP error bodies, the live AG-UI stream and its persisted copy, the process log. The
subprocess-environment layer is in :mod:`tests.test_agent`. The values searched for are the
ones the whole suite authenticates with, so requests still succeed while carrying them.
"""

import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app_spark_agent import settings
from app_spark_agent.masking import SECRET_PLACEHOLDER
from app_spark_agent.observability import LOGGER_NAME
from tests.api.support import (
    MODEL_API_KEY,
    RUNTIME_TOKEN,
    ApiFactory,
    drain_channel,
    run_request,
    run_turn,
)
from tests.support.ag_ui import SSE_HEADERS, assistant_text, run_body
from tests.support.fake_models import text_model

ALL_CREDENTIALS = (RUNTIME_TOKEN, MODEL_API_KEY)


def assert_no_credentials(text: str) -> None:
    """Fail with the offending value named, rather than with a bare False."""
    for credential in ALL_CREDENTIALS:
        assert credential not in text, f"{credential} leaked into: {text}"


def test_an_unauthorized_reply_does_not_name_the_expected_value(api: TestClient) -> None:
    """A 401 says the caller failed, not what would have worked."""
    # Bare client: the suite's auto-authentication would put the real token back on the request.
    raw = TestClient(api.app)
    body = run_body(conversation_id=str(uuid4()), run_id=str(uuid4()), context_version=0)

    refused = [
        raw.get("/health", headers={"Authorization": "Bearer wrong"}),
        raw.post("/runs", headers={"Authorization": "Bearer wrong"}, json=body),
    ]

    for resp in refused:
        assert resp.status_code == 401, resp.text
        assert_no_credentials(resp.text)


def test_a_rejected_query_value_is_masked_before_it_is_echoed(api: TestClient) -> None:
    """A validation error quotes the input it refused, and that input is the caller's.

    A declared query parameter on purpose: ``POST /runs`` parses the AG-UI document itself, so
    its 422 is a fixed string that echoes nothing and would pass this without any masking.
    """
    resp = api.get("/log", params={"since": RUNTIME_TOKEN})

    assert resp.status_code == 422
    # Proves the value reached the reply and was replaced, rather than never arriving.
    assert SECRET_PLACEHOLDER in resp.text
    assert_no_credentials(resp.text)


def test_a_refused_run_names_no_credential(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The 409 is built out of an exception's own text; the 503 is a fixed one.

    Sequenced, not split: the conflict needs a conversation to exist first, and dropping the
    key for the 503 is what stops any further run from starting.
    """
    run_turn(api, conversation_id=str(uuid4()))
    conflict = run_request(api, conversation_id=str(uuid4()), context_version=0)

    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    unready = run_request(api, conversation_id=str(uuid4()), context_version=0)

    assert conflict.status_code == 409, conflict.text
    assert unready.status_code == 503, unready.text
    assert_no_credentials(conflict.text)
    assert_no_credentials(unready.text)


_HALF = len(MODEL_API_KEY) // 2


@pytest.mark.parametrize(
    "chunks",
    [
        pytest.param((f"the key is {MODEL_API_KEY}",), id="whole-in-one-chunk"),
        pytest.param((MODEL_API_KEY[:_HALF], MODEL_API_KEY[_HALF:]), id="split-across-chunks"),
    ],
)
def test_the_stored_events_are_masked_however_the_model_chunked_the_value(
    make_api: ApiFactory,
    chunks: tuple[str, ...],
) -> None:
    """The stored copy is masked whether or not the value survived streaming in one piece.

    The model here does what a compromised or merely careless one would: repeats a credential
    verbatim. This is the case environment stripping cannot cover, because by then the value is
    model output. Both chunkings are covered because masking happens after the deltas of one
    message are joined, so the split is not a case the stored copy can fail on.
    """
    api = make_api(model=text_model(chunks))

    outcome = run_turn(api, conversation_id=str(uuid4()))

    # The live stream is forwarded untouched by design, so the client does see the value.
    assert MODEL_API_KEY in assistant_text(outcome.events)
    stored = drain_channel(api, "/ui-events")
    assert stored, "the run stored no events"
    assert_no_credentials(str(stored))
    # Proves the value reached the events and was replaced, rather than never arriving.
    assert SECRET_PLACEHOLDER in str(stored)


def test_the_tenant_label_changes_no_behaviour(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The label is for finding a sandbox's output, never for branching on."""
    observed: list[tuple[int, object, object]] = []
    for tenant in ("tenant-a", "tenant-b"):
        monkeypatch.setattr(settings, "TENANT_ID", tenant)

        health = api.get("/health").json()
        rejected = api.post("/runs", headers=SSE_HEADERS, json={"threadId": ""})

        observed.append((rejected.status_code, health["model_ready"], health["running"]))

    assert observed[0] == observed[1]


def test_a_run_is_logged_with_labels_and_without_credentials(
    api: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A run must be findable by session and tenant, and quote no credential doing it.

    The conversation id is caller-supplied, so it is the part of a log line that can carry
    anything -- the token included.
    """
    monkeypatch.setattr(settings, "SESSION_ID", "sess-demo")
    monkeypatch.setattr(settings, "TENANT_ID", "tenant-demo")

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        run_turn(api, conversation_id=f"conversation-{RUNTIME_TOKEN}")

    records = [record for record in caplog.records if record.name == LOGGER_NAME]
    assert records, "the run logged nothing"
    for record in records:
        assert record.session_id == "sess-demo"
        assert record.tenant_id == "tenant-demo"
        assert_no_credentials(record.getMessage())
    messages = [record.getMessage() for record in records]
    assert any("run started" in message for message in messages)
    assert any("run stream closed" in message for message in messages)
