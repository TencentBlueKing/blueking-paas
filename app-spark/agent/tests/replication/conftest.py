"""A control plane that lives in the test process, and the pieces wired to talk to it."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import pytest

from app_spark_agent.replication import ControlPlaneClient, StateReplicator
from app_spark_agent.state import AppendLog, ChangeSignal, Channel, ContextStore, CursorStore

BASE_URL = "http://control-plane.invalid/state/"

TOKEN = "test-token"


@dataclass
class FakeControlPlane:
    """An ingest endpoint that records what it was given and can be told to misbehave.

    Driven through ``httpx.MockTransport`` rather than over a socket, so a test asserts on the
    exact batches the replicator chose to send instead of on whatever a real server happened to
    log.

    :param failures: How many of the next calls to reject before answering normally, so that a
        failed pass can be shown to be retried rather than skipped over.
    :param truncate_to: Channels this endpoint should *lose* entries above the given sequence
        number on every write, which is the one thing that can legitimately move its answer
        backwards.
    :param truncate_once: The same, but only on the next write to that channel -- a control
        plane that dropped one batch and then recovered, which is what a re-send has to repair.
    :param context_ceiling: Highest context version this endpoint admits to holding, whatever it
        is sent. Stages a control plane whose archive did not move, which the replicator has to
        believe over its own version number.
    """

    channels: dict[str, list[dict[str, Any]]] = field(default_factory=dict[str, list[dict[str, Any]]])
    context: dict[str, Any] | None = None
    calls: list[tuple[str, int]] = field(default_factory=list[tuple[str, int]])
    failures: int = 0
    truncate_to: dict[str, int] = field(default_factory=dict[str, int])
    truncate_once: dict[str, int] = field(default_factory=dict[str, int])
    context_ceiling: int | None = None

    def last_seq(self, channel: str) -> int:
        """Return the highest sequence number held for a channel, the way ingest reports it."""
        stored = self.channels.get(channel, [])
        return int(stored[-1]["seq"]) if stored else 0

    def seqs(self, channel: str) -> list[int]:
        """Return the sequence numbers held for a channel, in order."""
        return [int(record["seq"]) for record in self.channels.get(channel, [])]

    def batches(self, channel: str) -> list[int]:
        """Return the size of each batch this channel was sent."""
        return [count for name, count in self.calls if name == channel]

    def transport(self) -> httpx.MockTransport:
        """Return a transport that answers as this control plane."""
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        name = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        self.calls.append((name, len(body.get("records", []))))

        if self.failures > 0:
            self.failures -= 1
            return httpx.Response(HTTPStatus.SERVICE_UNAVAILABLE, text="try again")

        if name == "context":
            version = int(body["context_version"])
            if self.context_ceiling is not None and version > self.context_ceiling:
                # Refused rather than archived, the way a control plane that already holds a
                # newer document answers: it reports what it kept, not what it was handed.
                return httpx.Response(HTTPStatus.OK, json={"context_version": self.context_ceiling})
            self.context = body
            return httpx.Response(HTTPStatus.OK, json={"context_version": version})

        self._store(name, body["records"])
        return httpx.Response(HTTPStatus.OK, json={"last_seq": self.last_seq(name)})

    def _store(self, channel: str, records: list[dict[str, Any]]) -> None:
        """Merge a batch the way a unique constraint on ``(conversation, seq)`` would."""
        stored = self.channels.setdefault(channel, [])
        held = {int(record["seq"]) for record in stored}
        stored.extend(record for record in records if int(record["seq"]) not in held)
        stored.sort(key=lambda record: int(record["seq"]))
        # The one-shot ceiling wins while it lasts, so a test can stage "lost this batch, kept
        # the next one" without having to reach in between two calls the replicator makes.
        ceiling = self.truncate_once.pop(channel, self.truncate_to.get(channel))
        if ceiling is not None:
            self.channels[channel] = [record for record in stored if int(record["seq"]) <= ceiling]


@dataclass
class Harness:
    """One Runtime's replicated state, plus the control plane it is replicating to."""

    control_plane: FakeControlPlane
    replicator: StateReplicator
    cursors: CursorStore
    signal: ChangeSignal
    transcript: AppendLog
    ui_events: AppendLog
    context_store: ContextStore


def make_replicator(
    control_plane: FakeControlPlane,
    *,
    cursors: CursorStore,
    signal: ChangeSignal,
    channels: Mapping[Channel, AppendLog],
    context_store: ContextStore,
    batch_size: int | None = None,
) -> StateReplicator:
    """Build a replicator wired to ``control_plane``, with retries fast enough for a test."""
    return StateReplicator(
        client=ControlPlaneClient(
            base_url=BASE_URL,
            token=TOKEN,
            transport=control_plane.transport(),
        ),
        cursors=cursors,
        signal=signal,
        channels=channels,
        context_store=context_store,
        batch_size=batch_size,
        retry_backoff_seconds=0.0,
    )


@pytest.fixture
def control_plane() -> FakeControlPlane:
    return FakeControlPlane()


@pytest.fixture
async def harness(tmp_path: Path, control_plane: FakeControlPlane) -> AsyncIterator[Harness]:
    """Assemble a replicator over real state files, pointed at the fake control plane."""
    signal = ChangeSignal()
    cursors = CursorStore(tmp_path / "cursors.json")
    transcript = AppendLog(tmp_path / "log.jsonl", payload_key="message", signal=signal)
    ui_events = AppendLog(tmp_path / "ui_events.jsonl", payload_key="event", signal=signal)
    context_store = ContextStore(tmp_path / "context.json", signal=signal)
    # Small enough that a handful of entries still exercise the batching loop.
    replicator = make_replicator(
        control_plane,
        cursors=cursors,
        signal=signal,
        channels={Channel.MESSAGE: transcript, Channel.UI_EVENT: ui_events},
        context_store=context_store,
        batch_size=2,
    )
    try:
        yield Harness(
            control_plane=control_plane,
            replicator=replicator,
            cursors=cursors,
            signal=signal,
            transcript=transcript,
            ui_events=ui_events,
            context_store=context_store,
        )
    finally:
        await replicator.aclose()
