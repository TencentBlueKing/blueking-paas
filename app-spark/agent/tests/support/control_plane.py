"""A control plane a real Runtime process can actually reach.

The in-process replication tests (:mod:`tests.replication`) construct a ``StateReplicator`` by
hand, which leaves one seam uncovered: whether ``create_app_from_settings()`` builds one at all
from ``APP_SPARK_AGENT_CONTROL_PLANE_*``. That seam can only be exercised by a Runtime spawned
the way a deployment spawns it, and such a Runtime is a separate process -- so the endpoint it
pushes to has to be on a real socket.

Kept deliberately dumb. It stores what it is given and answers with the cursor, which is the
whole contract; everything about *how* the control plane stores state belongs to the control
plane's own tests, not here.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from tests.support import console

TOKEN = "live-test-token"

# The conversation prefix a real control plane would bake into the address it hands out. Present
# so the test proves the Runtime appends its channel names *underneath* what it was given.
CONVERSATION_PATH = "/api/internal/conversations/live-test/state/"


class RecordedState:
    """What a control plane received, guarded for reads from the test's own thread.

    The server answers on its own threads while the test asserts on the main one, so every
    accessor takes the lock -- an unsynchronized read here would be a flaky test that only
    fails on a loaded machine.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._channels: dict[str, list[dict[str, Any]]] = {}
        self._context: dict[str, Any] | None = None

    def append(self, channel: str, records: list[dict[str, Any]]) -> int:
        """Store a batch idempotently and return the channel's resulting cursor."""
        with self._lock:
            stored = self._channels.setdefault(channel, [])
            held = {record["seq"] for record in stored}
            stored.extend(record for record in records if record["seq"] not in held)
            stored.sort(key=lambda record: int(record["seq"]))
            return int(stored[-1]["seq"]) if stored else 0

    def put_context(self, document: dict[str, Any]) -> int:
        """Archive a context document and return the version now held."""
        with self._lock:
            self._context = document
            return int(document["context_version"])

    def seqs(self, channel: str) -> list[int]:
        """Return the sequence numbers held for a channel, in order."""
        with self._lock:
            return [int(record["seq"]) for record in self._channels.get(channel, [])]

    def payloads(self, channel: str, key: str) -> list[Any]:
        """Return the body of every entry held for a channel."""
        with self._lock:
            return [record[key] for record in self._channels.get(channel, [])]

    @property
    def context(self) -> dict[str, Any] | None:
        """Return the archived context document, or ``None`` if none arrived."""
        with self._lock:
            return self._context


@contextmanager
def serve_control_plane() -> Generator[tuple[str, RecordedState]]:
    """Run an ingest endpoint on a loopback port for as long as the block lasts.

    :return: The conversation-scoped URL to hand the Runtime, and what it received.
    """
    state = RecordedState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address[:2]
    url = f"http://{host}:{port}{CONVERSATION_PATH}"
    console.banner(f"control plane listening on {url}")
    try:
        yield url, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _handler_for(state: RecordedState) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to one recorded state."""

    class Handler(BaseHTTPRequestHandler):
        # Silences the per-request line `BaseHTTPRequestHandler` writes straight to stderr,
        # which would interleave with the narration `-s` is passed for.
        def log_message(self, format: str, *args: Any) -> None: ...

        def do_POST(self) -> None:
            self._handle_append()

        def do_PUT(self) -> None:
            self._handle_context()

        def _handle_append(self) -> None:
            body = self._authorized_body()
            if body is None:
                return
            channel = self.path.rsplit("/", 1)[-1]
            last_seq = state.append(channel, body["records"])
            console.exchange(
                f"<- POST {channel}",
                HTTPStatus.OK,
                f"{len(body['records'])} record(s), last_seq={last_seq}",
            )
            self._reply({"last_seq": last_seq})

        def _handle_context(self) -> None:
            body = self._authorized_body()
            if body is None:
                return
            version = state.put_context(body)
            console.exchange("<- PUT  context", HTTPStatus.OK, f"context_version={version}")
            self._reply({"context_version": version})

        def _authorized_body(self) -> dict[str, Any] | None:
            """Read the request body, or answer 401 and return ``None``."""
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self._reply({"detail": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return None
            length = int(self.headers.get("Content-Length", 0))
            payload: dict[str, Any] = json.loads(self.rfile.read(length))
            return payload

        def _reply(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler
