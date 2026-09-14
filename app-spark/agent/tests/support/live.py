"""Starting a real Runtime process, and driving it the way a client would.

The Runtime exposes an ASGI application and nothing else, so a live test starts it exactly the
way a deployment does: an external ASGI server pointed at ``app_spark_agent.server.asgi:app``,
configured entirely through ``APP_SPARK_AGENT_*`` variables. Nothing here reaches into the
process it started -- every assertion a test makes travels over HTTP, and the state directory
is only ever read through the endpoints that serve it.

Nothing here is tied to a particular model: :mod:`tests.e2e` drives these against the real one,
and :mod:`tests.live` drives them against ``fake:`` scenarios that cost nothing.

Every call narrates itself through :mod:`tests.support.console`, which makes ``-s`` worth
passing.
"""

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx

from app_spark_agent import settings
from tests.support import console
from tests.support.ag_ui import run_body

ASGI_TARGET = "app_spark_agent.server.asgi:app"
ENV_PREFIX = settings.ENV_PREFIX

SSE_HEADERS = {"Accept": "text/event-stream"}
E2E_RUNTIME_TOKEN = "e2e-runtime-token"

# Startup only waits on a Python import; a turn waits on a real model that may be writing files.
STARTUP_TIMEOUT_SECONDS = 30.0
REQUEST_TIMEOUT_SECONDS = 180.0

# How much of the server's own log to show when it refuses to start.
LOG_TAIL_LINES = 40


@dataclass(frozen=True)
class Turn:
    """One completed run, as the client saw it."""

    events: list[dict[str, Any]]
    reply: str
    seconds: float

    @property
    def event_types(self) -> list[str]:
        """Return the type of every streamed event, in order."""
        return [str(event.get("type")) for event in self.events]

    @property
    def tool_calls(self) -> list[str]:
        """Return the name of every tool the model invoked, in order."""
        return [str(event["toolCallName"]) for event in self.events if event.get("type") == "TOOL_CALL_START"]


class LiveRuntime:
    """A Runtime process under test, and a client that narrates every call it makes."""

    def __init__(
        self,
        *,
        label: str,
        url: str,
        state_dir: Path,
        process: subprocess.Popen[bytes],
        client: httpx.Client,
        log_path: Path,
    ) -> None:
        self.label = label
        self.url = url
        self.state_dir = state_dir
        self._process = process
        self._client = client
        self._log_path = log_path
        self._stopped = False

    def health(self) -> dict[str, Any]:
        """Return the Runtime's cursors, the way a control plane polls them."""
        health = cast(dict[str, Any], self._client.get("/health").json())
        console.exchange(
            "GET  /health",
            200,
            " ".join(
                f"{key}={health[key]}" for key in ("conversation_id", "context_version", "log_seq", "ui_event_seq")
            ),
        )
        return health

    def context(self) -> dict[str, Any]:
        """Export the context the next run would be given."""
        response = self._client.get("/context")
        exported = cast(dict[str, Any], response.json())
        console.exchange(
            "GET  /context",
            response.status_code,
            f"etag={response.headers.get('etag')} messages={len(exported['messages'])}",
        )
        return exported

    def restore(
        self,
        context: dict[str, Any],
        *,
        if_match: str | None = None,
        log_seq: int | None = None,
        ui_event_seq: int | None = None,
    ) -> httpx.Response:
        """Inject a cold context, and return the response without judging it.

        Both outcomes are part of the contract -- a mismatched ``If-Match`` is a 412, an
        occupied Runtime is a 409 -- so the status is the caller's to assert on.

        :param context: The document ``GET /context`` produced, passed through unchanged.
        :param if_match: Version the Runtime is expected to currently hold.
        :param log_seq: Sequence number the transcript should continue from. Omitted means the
            conversation has no history anywhere else and numbering starts at 1.
        :param ui_event_seq: Sequence number the AG-UI history should continue from.
        """
        headers = {"If-Match": if_match} if if_match is not None else {}
        params = {
            name: value for name, value in (("log_seq", log_seq), ("ui_event_seq", ui_event_seq)) if value is not None
        }
        response = self._client.put("/context", json=context, headers=headers, params=params)
        described = " ".join(
            [
                *([f"If-Match={if_match}"] if if_match is not None else []),
                *(f"{name}={value}" for name, value in params.items()),
                console.clip(response.text, limit=60),
            ]
        )
        console.exchange("PUT  /context", response.status_code, described)
        return response

    def drain(self, channel: str) -> list[dict[str, Any]]:
        """Read an append-only channel to its end, one cursor at a time."""
        records: list[dict[str, Any]] = []
        pages = 0
        since = 0
        while True:
            page = cast(
                dict[str, Any],
                self._client.get(f"/{channel}", params={"since": since}).json(),
            )
            pages += 1
            page_records = cast(list[dict[str, Any]], page["records"])
            records.extend(page_records)
            if not page_records or records[-1]["seq"] >= page["last_seq"]:
                break
            since = records[-1]["seq"]
        console.exchange(
            f"GET  /{channel}",
            200,
            f"{len(records)} records in {pages} page(s)",
        )
        return records

    def turn(
        self,
        *,
        conversation_id: str,
        prompt: str,
        context_version: int | None = None,
    ) -> Turn:
        """Run one conversation turn, printing the model's answer as it arrives.

        The version defaults to whatever the Runtime currently holds, which is also what a
        client has to do: compaction can move it more than once inside a single run, so it is
        read back rather than counted.

        :param conversation_id: Conversation this turn belongs to.
        :param prompt: User message to send.
        :param context_version: Version to submit, read from ``/health`` when omitted.
        :return: The events the run streamed and the reply they spell out.
        """
        version = self.health()["context_version"] if context_version is None else context_version
        console.request("POST /runs", f"contextVersion={version}")
        console.line(f"{console.INDENT}user > {console.clip(prompt)}")

        printer = console.StreamPrinter()
        events: list[dict[str, Any]] = []
        started = time.monotonic()
        with self._client.stream(
            "POST",
            "/runs",
            headers=SSE_HEADERS,
            json=run_body(
                conversation_id=conversation_id,
                run_id=str(uuid4()),
                context_version=version,
                prompt=prompt,
            ),
        ) as response:
            if response.status_code != 200:
                response.read()
                console.exchange("POST /runs", response.status_code, console.clip(response.text))
                raise AssertionError(f"the Runtime refused the run: {response.text}")
            for event in iter_sse(response):
                events.append(event)
                printer.feed(event)
            printer.close()

        seconds = time.monotonic() - started
        console.exchange("POST /runs", 200, f"{len(events)} events in {seconds:.1f}s")
        return Turn(events=events, reply=assistant_reply(events), seconds=seconds)

    def stop(self) -> None:
        """Stop the process and close the client. Safe to call more than once.

        Called explicitly by the restart scenario, where the whole point is that the second
        process finds on disk what the first one left behind.
        """
        if self._stopped:
            return
        self._stopped = True
        self._client.close()
        # A Runtime that is already gone was not stopped by this test: it died on its own, and
        # whatever failure is being reported above is a connection error that cannot say why.
        if self._process.poll() is not None:
            console.note(f"{self.label} had already exited:\n{tail(self._log_path)}")
            return
        terminate(self._process)
        console.note(f"{self.label} stopped")


@contextmanager
def serve(
    *,
    workspace: Path,
    state_dir: Path,
    label: str,
    **overrides: str,
) -> Generator[LiveRuntime]:
    """Start a Runtime under uvicorn and yield it once it answers ``/health``.

    :param workspace: Directory exposed to the agent's tools.
    :param state_dir: Directory holding the conversation's durable state.
    :param label: Name this Runtime is reported under; several may run in one test.
    :param overrides: Extra settings, passed under their ``APP_SPARK_AGENT_`` names.
    """
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    log_path = state_dir.parent / f"{label}-uvicorn.log"
    runtime_token = os.environ.get(f"{ENV_PREFIX}RUNTIME_TOKEN") or E2E_RUNTIME_TOKEN
    # Prefer the already-resolved setting (including `.env`) over `os.environ`: injecting an
    # empty string would block the child from reading its own `.env` and leave it unready.
    model_api_key = settings.MODEL_API_KEY or ""

    console.banner(f"{label}: uvicorn {ASGI_TARGET} on {url}")
    console.note(f"workspace={workspace}")
    console.note(f"state-dir={state_dir}")
    for key, value in overrides.items():
        console.note(f"{ENV_PREFIX}{key}={value}")

    # The child's output goes to a file rather than a pipe: nothing reads it while the Runtime
    # is up, and a pipe nobody drains blocks the server once it fills.
    log_handle = log_path.open("wb")
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                ASGI_TARGET,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--timeout-graceful-shutdown",
                str(settings.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS),
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env={
                **os.environ,
                f"{ENV_PREFIX}WORKSPACE": str(workspace),
                f"{ENV_PREFIX}STATE_DIR": str(state_dir),
                f"{ENV_PREFIX}RUNTIME_TOKEN": runtime_token,
                f"{ENV_PREFIX}MODEL_API_KEY": model_api_key,
                f"{ENV_PREFIX}IDLE_TIMEOUT_SECONDS": "0",
                **{f"{ENV_PREFIX}{key}": value for key, value in overrides.items()},
            },
        )
    finally:
        log_handle.close()

    started = time.monotonic()
    try:
        wait_until_healthy(url, process, log_path, runtime_token)
    except BaseException:
        terminate(process)
        raise
    console.note(f"{label} healthy in {time.monotonic() - started:.1f}s")

    runtime = LiveRuntime(
        label=label,
        url=url,
        state_dir=state_dir,
        process=process,
        client=httpx.Client(
            base_url=url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {runtime_token}"},
        ),
        log_path=log_path,
    )
    try:
        yield runtime
    finally:
        runtime.stop()


def wait_until_healthy(
    url: str,
    process: subprocess.Popen[bytes],
    log_path: Path,
    runtime_token: str,
) -> None:
    """Poll ``/health`` until the Runtime answers, or explain why it never will.

    A configuration error kills the server during import, long before the deadline, so the
    process is checked on every pass: saying so immediately beats spending the whole timeout
    polling something that already exited.
    """
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while True:
        try:
            if (
                httpx.get(
                    f"{url}/health",
                    headers={"Authorization": f"Bearer {runtime_token}"},
                    timeout=0.5,
                ).status_code
                == 200
            ):
                return
        except httpx.HTTPError:
            pass
        if process.poll() is not None:
            raise AssertionError(f"Runtime exited during startup:\n{tail(log_path)}")
        if time.monotonic() >= deadline:
            raise AssertionError(f"Runtime never became healthy:\n{tail(log_path)}")
        time.sleep(0.05)


def terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop a Runtime process, escalating only if it refuses to go."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def tail(log_path: Path, lines: int = LOG_TAIL_LINES) -> str:
    """Return the end of a Runtime's own log, for a failure that has to be explained."""
    if not log_path.exists():
        return "(the Runtime wrote no log)"
    return "\n".join(log_path.read_text(errors="replace").splitlines()[-lines:])


def free_port() -> int:
    """Reserve a loopback port and hand it back, so the server can be told where to listen.

    The Runtime does not start itself, so there is no startup line to read a chosen port from:
    the port has to be decided before the server is launched.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def iter_sse(response: httpx.Response) -> Iterator[dict[str, Any]]:
    """Yield each AG-UI event as it arrives, rather than after the stream ends."""
    data: list[str] = []
    for raw in response.iter_lines():
        stripped = raw.rstrip("\r")
        if stripped.startswith("data:"):
            data.append(stripped.removeprefix("data:").lstrip())
        elif not stripped and data:
            yield cast(dict[str, Any], json.loads("\n".join(data)))
            data = []
    if data:
        yield cast(dict[str, Any], json.loads("\n".join(data)))


def assistant_reply(events: Sequence[dict[str, Any]]) -> str:
    """Return the assistant's message, reassembled from its text deltas."""
    return "".join(
        str(event["delta"])
        for event in events
        if event.get("type") == "TEXT_MESSAGE_CONTENT" and isinstance(event.get("delta"), str)
    )


# --- Reading what a drained channel came back with -------------------------------------------
# Both channels wrap their payload in a record carrying the cursor, so a test that wants the
# conversation has to unwrap it first. Shared because more than one scenario asks the same
# questions of the same two channels.


def model_messages(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the model messages inside drained ``/log`` records."""
    return [cast(dict[str, Any], record["message"]) for record in records]


def stored_events(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the AG-UI events inside drained ``/ui-events`` records."""
    return [cast(dict[str, Any], record["event"]) for record in records]


def part_contents(messages: Sequence[dict[str, Any]]) -> list[str]:
    """Return the text of every message part that carries string content."""
    return [
        part["content"] for message in messages for part in message["parts"] if isinstance(part.get("content"), str)
    ]


def part_kinds(messages: Sequence[dict[str, Any]]) -> set[str]:
    """Return every kind of part the messages are made of."""
    return {part["part_kind"] for message in messages for part in message["parts"]}
