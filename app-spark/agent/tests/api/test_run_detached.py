"""A run belongs to the Runtime, not to the connection that started it.

The SSE response only follows a run. These tests pin down the two consequences: a client that
hangs up leaves a turn that still runs to its end and lands like any other, and the way to end a
turn early is to ask for it, by name, with ``POST /runs/{run_id}/stop``.
"""

import asyncio
import json
import time
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx2
import pytest
from fastapi import FastAPI

from app_spark_agent.server.runtime import ConversationRuntime
from tests.api.support import (
    AUTH_HEADERS,
    BUSY_TIMEOUT_SECONDS,
    build_test_client,
    http_client,
)
from tests.support.ag_ui import SSE_HEADERS, run_body, sse_events
from tests.support.fake_models import gated_model

# Every test here starts a fresh Runtime, so any conversation id is a valid one to begin with.
CONVERSATION_ID = str(uuid4())


async def post_run(
    client: httpx2.AsyncClient,
    *,
    run_id: str,
    prompt: str = "hello",
    context_version: int = 0,
) -> httpx2.Response:
    """Post a turn of the shared conversation, with a run id the test chose and can stop by."""
    return await client.post(
        "/runs",
        headers=SSE_HEADERS,
        json=run_body(
            conversation_id=CONVERSATION_ID,
            run_id=run_id,
            context_version=context_version,
            prompt=prompt,
        ),
    )


async def wait_until_running(client: httpx2.AsyncClient, run_id: str) -> None:
    """Block until the named run has started, not merely been admitted.

    ``running`` goes true as soon as the guard is taken, which is a few awaits before the run
    exists to be stopped or named; a test acting on it in that window would race the handshake.
    """
    deadline = time.monotonic() + BUSY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if (await client.get("/health")).json()["run_id"] == run_id:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"run {run_id} never started")


async def wait_until_idle(client: httpx2.AsyncClient, timeout: float = BUSY_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Block until no run holds the Runtime, and return the health that said so."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health: dict[str, Any] = (await client.get("/health")).json()
        if not health["running"]:
            return health
        await asyncio.sleep(0.01)
    raise AssertionError("the run never finished")


async def ui_event_types(client: httpx2.AsyncClient) -> list[str]:
    page: dict[str, Any] = (await client.get("/ui-events", params={"limit": 1000})).json()
    return [record["event"]["type"] for record in page["records"]]


async def hang_up_after_first_chunk(app: Any, body: dict[str, object]) -> None:
    """Send one run straight to the ASGI app, then disconnect once the first event is out.

    Driven by hand rather than through httpx, because what is under test is precisely the
    ``http.disconnect`` message a server delivers when the browser goes away.
    """
    payload = json.dumps(body).encode()
    first_chunk = asyncio.Event()
    request_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": payload, "more_body": False}
        await first_chunk.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            assert message["status"] == 200
        if message["type"] == "http.response.body" and message.get("body"):
            first_chunk.set()

    headers = {**AUTH_HEADERS, **SSE_HEADERS, "Content-Type": "application/json"}
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/runs",
        "raw_path": b"/runs",
        "query_string": b"",
        "root_path": "",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": ("127.0.0.1", 1234),
        "server": ("runtime.test", 80),
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=BUSY_TIMEOUT_SECONDS)


@pytest.fixture
def save_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Record what each turn's workspace commit was told, without a Git repository."""
    calls: list[dict[str, Any]] = []
    original = ConversationRuntime.save_workspace

    async def recording(self: ConversationRuntime, **kwargs: Any) -> None:
        calls.append(kwargs)
        await original(self, **kwargs)

    monkeypatch.setattr(ConversationRuntime, "save_workspace", recording)
    return calls


async def test_a_run_outlives_a_client_that_hangs_up(tmp_path: Path, save_calls: list[dict[str, Any]]) -> None:
    gate = asyncio.Event()
    test_client = build_test_client(tmp_path, model=gated_model(gate, reply="still here"))
    conversation_id = str(uuid4())
    body = run_body(conversation_id=conversation_id, run_id=str(uuid4()), context_version=0)

    async with http_client(test_client) as client:
        await hang_up_after_first_chunk(test_client.app, body)

        # The response is gone, and the turn is not.
        assert (await client.get("/health")).json()["running"] is True

        gate.set()
        health = await wait_until_idle(client)

        assert health["context_version"] == 1
        types = await ui_event_types(client)
        assert types[-1] == "RUN_FINISHED"
        assert "TEXT_MESSAGE_CONTENT" in types
        context: dict[str, Any] = (await client.get("/context")).json()
        assert "still here" in json.dumps(context["messages"])
        assert [call["completed"] for call in save_calls] == [True]


async def test_health_names_the_run_in_progress(tmp_path: Path) -> None:
    gate = asyncio.Event()
    test_client = build_test_client(tmp_path, model=gated_model(gate))
    run_id = str(uuid4())

    async with http_client(test_client) as client:
        assert (await client.get("/health")).json()["run_id"] is None
        streaming = asyncio.create_task(post_run(client, run_id=run_id))
        await wait_until_running(client, run_id)
        assert (await client.get("/health")).json()["running"] is True

        gate.set()
        await streaming
        assert (await client.get("/health")).json()["run_id"] is None


async def test_a_stopped_run_ends_like_a_finished_one(tmp_path: Path, save_calls: list[dict[str, Any]]) -> None:
    # Never released: only the stop can end this turn.
    gate = asyncio.Event()
    test_client = build_test_client(tmp_path, model=gated_model(gate))
    run_id = str(uuid4())

    async with http_client(test_client) as client:
        streaming = asyncio.create_task(post_run(client, run_id=run_id, prompt="build me a page"))
        await wait_until_running(client, run_id)

        stopped = await client.post(f"/runs/{run_id}/stop")
        assert stopped.status_code == 202, stopped.text
        assert stopped.json() == {"run_id": run_id, "stopping": True}
        # Asking twice is not an error: the client may not know whether the first one landed.
        assert (await client.post(f"/runs/{run_id}/stop")).status_code == 202

        response = await asyncio.wait_for(streaming, timeout=BUSY_TIMEOUT_SECONDS)
        assert response.status_code == 200
        assert [event["type"] for event in sse_events(response.text)][-1] == "RUN_FINISHED"

        health: dict[str, Any] = (await client.get("/health")).json()
        assert health["running"] is False
        assert health["run_id"] is None
        # Stopped is not lost: the next turn's model is told this one happened.
        assert health["context_version"] == 1
        context: dict[str, Any] = (await client.get("/context")).json()
        assert "build me a page" in json.dumps(context["messages"])
        assert [call["completed"] for call in save_calls] == [False]

        # It is over, so there is nothing left to stop.
        assert (await client.post(f"/runs/{run_id}/stop")).status_code == 404


async def test_a_stop_for_another_run_leaves_the_current_one_alone(tmp_path: Path) -> None:
    gate = asyncio.Event()
    test_client = build_test_client(tmp_path, model=gated_model(gate))

    async with http_client(test_client) as client:
        run_id = str(uuid4())
        streaming = asyncio.create_task(post_run(client, run_id=run_id))
        await wait_until_running(client, run_id)

        assert (await client.post(f"/runs/{uuid4()}/stop")).status_code == 404

        gate.set()
        response = await streaming
        assert "TEXT_MESSAGE_CONTENT" in [event["type"] for event in sse_events(response.text)]


def test_stopping_needs_the_runtime_token(tmp_path: Path) -> None:
    test_client = build_test_client(tmp_path, model=gated_model(asyncio.Event()))
    assert test_client.post(f"/runs/{uuid4()}/stop", headers={"Authorization": "Bearer wrong"}).status_code == 401


async def test_shutting_down_stops_the_run_in_progress(tmp_path: Path, save_calls: list[dict[str, Any]]) -> None:
    gate = asyncio.Event()
    test_client = build_test_client(tmp_path, model=gated_model(gate))
    app = cast(FastAPI, test_client.app)
    runtime: ConversationRuntime = app.state.conversation_runtime

    async with http_client(test_client) as client:
        lifespan: AbstractAsyncContextManager[None] = app.router.lifespan_context(app)
        async with lifespan:
            run_id = str(uuid4())
            streaming = asyncio.create_task(post_run(client, run_id=run_id, prompt="unfinished"))
            await wait_until_running(client, run_id)
        # Leaving the lifespan is the server shutting down.

        assert runtime.run_guard.busy is False
        assert runtime.context_store.context.context_version == 1
        assert [call["completed"] for call in save_calls] == [False]
        response = await streaming
        assert [event["type"] for event in sse_events(response.text)][-1] == "RUN_FINISHED"

        # A run admitted after that, however briefly, would get no wind-down: it is refused.
        late = await post_run(client, run_id=str(uuid4()), context_version=1)
        assert late.status_code == 503, late.text
        assert runtime.run_guard.busy is False
