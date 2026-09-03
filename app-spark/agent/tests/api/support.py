"""Clients and scenarios shared by the in-process Runtime API tests.

This module owns everything that drives the test application over HTTP.
"""

import asyncio
import time
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.models.function import FunctionModel

from app_spark_agent.server import create_runtime_app
from tests.support.ag_ui import SSE_HEADERS, assistant_text, run_body, sse_events
from tests.support.fake_models import gated_model

# Both are at least sixteen characters and share no substring, so a leak test can search for
# one without matching the other or matching ordinary output.
RUNTIME_TOKEN = "test-runtime-token"
MODEL_API_KEY = "test-model-api-key"
AUTH_HEADERS = {"Authorization": f"Bearer {RUNTIME_TOKEN}"}
HEALTH_FIELDS = {"version", "model_ready", "running", "app_status"}

# `ASGITransport` never opens a socket, so this only has to be an absolute URL httpx can build
# requests from; nothing ever resolves it.
ASGI_BASE_URL = "http://runtime.test"


class AuthedTestClient(TestClient):
    """TestClient that attaches the runtime Bearer."""

    def request(self, method: str, url: str, **kwargs: Any) -> Any:  # type: ignore[override]
        headers = {str(key): str(value) for key, value in dict(kwargs.get("headers") or {}).items()}
        # Keep a caller-supplied Authorization so 401 cases can be tested.
        if not any(key.lower() == "authorization" for key in headers):
            headers["Authorization"] = AUTH_HEADERS["Authorization"]
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


# Long enough to survive a loaded machine, short enough that a guard that is never taken fails
# the test instead of hanging the suite.
BUSY_TIMEOUT_SECONDS = 5.0


class ApiFactory(Protocol):
    """Build one started Runtime per call."""

    def __call__(
        self,
        *,
        model: FunctionModel | None = None,
        capabilities: Sequence[AbstractCapability[object]] = (),
        tools: Sequence[Any] = (),
    ) -> TestClient: ...


def build_test_client(
    tmp_path: Path,
    *,
    model: FunctionModel,
    capabilities: Sequence[AbstractCapability[object]] = (),
    tools: Sequence[Any] = (),
) -> TestClient:
    """Create a Runtime wired to a fake model, bypassing the real DeepSeek agent."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    state_dir = tmp_path / "state"
    agent: Agent[object, str] = Agent(
        model,
        tools=list(tools),
        capabilities=list[AbstractCapability[object]](capabilities),
    )
    app = create_runtime_app(workspace=workspace, state_dir=state_dir, agent=agent)
    return AuthedTestClient(app)


def run_request(
    client: TestClient,
    *,
    conversation_id: str,
    context_version: int,
    prompt: str = "hello",
    run_id: str | None = None,
) -> Any:
    """Post one AG-UI run and return the raw HTTP response."""
    return client.post(
        "/runs",
        headers=SSE_HEADERS,
        json=run_body(
            conversation_id=conversation_id,
            run_id=run_id or str(uuid4()),
            context_version=context_version,
            prompt=prompt,
        ),
    )


def drain_channel(
    client: TestClient,
    channel: str,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read an append-only channel to its end the way the control plane does.

    :param client: Client the Runtime is reached through.
    :param channel: Drain endpoint, ``/log`` or ``/ui-events``.
    :param limit: Page size, left to the endpoint's own default when omitted.
    :return: Every record in the channel, in sequence order.
    """
    records: list[dict[str, Any]] = []
    since = 0
    while True:
        params: dict[str, int] = {"since": since}
        if limit is not None:
            params["limit"] = limit
        response = client.get(channel, params=params)
        assert response.status_code == 200, response.text
        page = cast(dict[str, Any], response.json())
        page_records = cast(list[dict[str, Any]], page["records"])
        records.extend(page_records)
        if not page_records or records[-1]["seq"] >= page["last_seq"]:
            return records
        since = records[-1]["seq"]


def get_transcript_messages(client: TestClient) -> list[dict[str, Any]]:
    """Return the raw model messages exposed by the Runtime, in order."""
    return [cast(dict[str, Any], record["message"]) for record in drain_channel(client, "/log")]


def get_context(client: TestClient) -> dict[str, Any]:
    """Return the conversation context exposed by the Runtime."""
    response = client.get("/context")
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


@dataclass(frozen=True)
class RunOutcome:
    """One finished run, represented by the AG-UI events the client received."""

    events: list[dict[str, Any]]
    content_type: str

    @property
    def reply(self) -> str:
        """Return the assistant message, reassembled from the deltas the client received."""
        return assistant_text(self.events)

    @property
    def event_types(self) -> list[str]:
        """Return the type of every streamed event, in order."""
        return [event["type"] for event in self.events]


def run_turn(
    client: TestClient,
    *,
    conversation_id: str,
    prompt: str = "hello",
    run_id: str | None = None,
) -> RunOutcome:
    """Drive one successful turn at the Runtime's current context version.

    The version is read back rather than counted, because compaction may move it more than once
    inside a single run.
    """
    version: int = client.get("/health").json()["context_version"]
    response = run_request(
        client,
        conversation_id=conversation_id,
        context_version=version,
        prompt=prompt,
        run_id=run_id,
    )
    assert response.status_code == 200, response.text
    return RunOutcome(
        events=sse_events(response.text),
        content_type=response.headers["content-type"],
    )


@asynccontextmanager
async def http_client(test_client: TestClient) -> AsyncGenerator[httpx.AsyncClient]:
    """Reach a Runtime from the test's own event loop.

    ``TestClient`` runs each request to completion before returning, which is precisely what a
    test about two overlapping requests cannot use. Driving the ASGI application directly keeps
    both requests on one event loop, so the second one arrives while the first is still open.
    """
    transport = httpx.ASGITransport(app=test_client.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url=ASGI_BASE_URL,
        headers=AUTH_HEADERS,
    ) as client:
        yield client


async def post_run_async(
    client: httpx.AsyncClient,
    *,
    conversation_id: str,
    context_version: int,
    prompt: str = "hello",
) -> httpx.Response:
    """Post one AG-UI run over an event-loop-sharing client and return its response."""
    return await client.post(
        "/runs",
        headers=SSE_HEADERS,
        json=run_body(
            conversation_id=conversation_id,
            run_id=str(uuid4()),
            context_version=context_version,
            prompt=prompt,
        ),
    )


@dataclass(frozen=True)
class InFlightRun:
    """A Runtime with one run held open, and a client that can reach it meanwhile."""

    client: httpx.AsyncClient
    conversation_id: str
    gate: asyncio.Event
    streaming: asyncio.Task[httpx.Response]

    async def release(self) -> httpx.Response:
        """Let the held run finish and return the response it streamed.

        Safe to call more than once, and called on the way out of :func:`run_in_flight` for the
        test that forgot to: an unreleased run would leave a task waiting on a gate forever.
        """
        self.gate.set()
        return await self.streaming


async def wait_until_busy(
    client: httpx.AsyncClient,
    timeout: float = BUSY_TIMEOUT_SECONDS,
) -> None:
    """Block until the Runtime reports a run in flight, or fail the test."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health: dict[str, Any] = (await client.get("/health")).json()
        if health["running"]:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("the Runtime never reported a run in flight")


@asynccontextmanager
async def run_in_flight(tmp_path: Path) -> AsyncGenerator[InFlightRun]:
    """Start a run that cannot finish until released, and yield the busy Runtime."""
    gate = asyncio.Event()
    test_client = build_test_client(tmp_path, model=gated_model(gate))
    conversation_id = str(uuid4())
    async with http_client(test_client) as client:
        streaming = asyncio.create_task(post_run_async(client, conversation_id=conversation_id, context_version=0))
        held = InFlightRun(
            client=client,
            conversation_id=conversation_id,
            gate=gate,
            streaming=streaming,
        )
        try:
            await wait_until_busy(client)
            yield held
        finally:
            await held.release()
