"""The live objects one Runtime process serves a single conversation from.

This module knows nothing about HTTP. It owns what the views operate on -- the three durable
state channels, the agent, and the guard that keeps runs from overlapping -- so the view layer
in :mod:`app_spark_agent.server.routes` is left with nothing but request and response handling.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import Agent

from app_spark_agent.agent import create_agent
from app_spark_agent.server.lifecycle import RuntimeLifecycle
from app_spark_agent.state import AppendLog, ContextStore

# The on-disk names of the three state channels. Deliberately not configurable: they are the
# contract the control plane reads a state directory by, so renaming one is a migration rather
# than a deployment knob.
CONTEXT_FILENAME = "context.json"
TRANSCRIPT_FILENAME = "log.jsonl"
UI_EVENTS_FILENAME = "ui_events.jsonl"


class RuntimeBusyError(RuntimeError):
    """Raised when an exclusive operation is attempted while another one holds the runtime."""


class RunLease:
    """Hold the single run slot until :meth:`release`.

    If Starlette never iterates the SSE generator, :meth:`release_if_never_started`
    still frees the slot so a failed handshake cannot leave the Runtime busy.
    """

    def __init__(self, guard: RunGuard, on_release: Callable[[], None] | None = None) -> None:
        self._guard = guard
        self._on_release = on_release
        self._entered = False
        self._released = False

    def mark_entered(self) -> None:
        """Mark that the SSE generator has started."""
        self._entered = True

    def release(self) -> None:
        """Release the slot. Safe to call more than once."""
        if self._released:
            return
        self._released = True
        self._guard.release()
        if self._on_release is not None:
            self._on_release()

    def release_if_never_started(self) -> None:
        """Release only if the SSE generator never started."""
        if not self._entered:
            self.release()


class RunGuard:
    """Serialize everything that may mutate the conversation.

    One process owns exactly one conversation, so a run and a cold-context restore must never
    overlap. Both callers need the same "reject rather than queue" behaviour, which is why the
    check and the acquisition live here together: ``asyncio.Lock.acquire`` claims an uncontended
    lock without awaiting anything, so testing :attr:`busy` and then acquiring cannot interleave
    with another request. Splitting the two across call sites would quietly lose that guarantee.
    """

    # TODO: an asyncio lock cannot protect across processes; replace with a file lock.

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._on_run_end: Callable[[], None] | None = None

    def notify_run_end(self, callback: Callable[[], None]) -> None:
        """Call ``callback`` after each run releases the slot. The idle clock starts here."""
        self._on_run_end = callback

    @property
    def busy(self) -> bool:
        """Return whether an exclusive operation currently holds the guard."""
        return self._lock.locked()

    async def acquire(self) -> None:
        """Take the guard, or refuse when it is already held.

        Paired with :meth:`release` only when the holder outlives the request handler, as a
        streaming run does; anything simpler should use :meth:`exclusive`.

        :raises RuntimeBusyError: If another exclusive operation is in progress.
        """
        if self._lock.locked():
            raise RuntimeBusyError("An Agent run is already in progress.")
        await self._lock.acquire()

    async def try_acquire(self) -> RunLease | None:
        """Take the slot as a :class:`RunLease`, or return ``None`` if it is already held."""
        try:
            await self.acquire()
        except RuntimeBusyError:
            return None
        return RunLease(self, on_release=self._on_run_end)

    def release(self) -> None:
        """Hand the guard back so the next exclusive operation can be admitted."""
        self._lock.release()

    @asynccontextmanager
    async def exclusive(self) -> AsyncGenerator[None]:
        """Hold the guard for the duration of the block.

        Does not reset the idle clock. Only ``POST /runs`` does that, when its
        :class:`RunLease` is released.

        :raises RuntimeBusyError: If another exclusive operation is in progress.
        """
        await self.acquire()
        try:
            yield
        finally:
            self.release()


@dataclass(frozen=True)
class ConversationRuntime:
    """One conversation's agent, durable state, and concurrency guard.

    :param agent: Agent every run of this conversation is driven by.
    :param context_store: The mutable context compaction rewrites; the only cold-start source.
    :param transcript: Append-only channel holding the raw model messages.
    :param ui_events: Append-only channel holding the AG-UI events the client saw.
    :param run_guard: Guard admitting one mutating operation at a time.
    :param lifecycle: Idle timeout and the registry of application children.
    """

    agent: Agent[Any, Any]
    context_store: ContextStore
    transcript: AppendLog
    ui_events: AppendLog
    run_guard: RunGuard
    lifecycle: RuntimeLifecycle

    @classmethod
    def open(
        cls,
        *,
        workspace: Path,
        state_dir: Path,
        agent: Agent[Any, Any] | None = None,
        lifecycle: RuntimeLifecycle | None = None,
    ) -> ConversationRuntime:
        """Validate the two directories and open the conversation's three state channels.

        :param workspace: Existing directory exposed to coding tools.
        :param state_dir: Directory outside ``workspace`` holding the durable state; created
            with owner-only permissions when missing.
        :param agent: Optional preconfigured agent, primarily for embedding or for tests.
        :param lifecycle: Optional idle / SIGTERM controller; created from settings when omitted.
        :return: A runtime ready to be served.
        :raises FileNotFoundError: If ``workspace`` does not exist.
        :raises NotADirectoryError: If ``workspace`` is not a directory.
        :raises ValueError: If ``state_dir`` overlaps ``workspace``.
        """
        resolved_workspace = workspace.expanduser().resolve(strict=True)
        if not resolved_workspace.is_dir():
            raise NotADirectoryError(f"Workspace is not a directory: {resolved_workspace}")

        resolved_state_dir = state_dir.expanduser().resolve()
        # State inside the workspace would be readable and writable by the agent's own file and
        # shell tools, which is both a leak and a way for a run to corrupt its own history.
        if _paths_overlap(resolved_workspace, resolved_state_dir):
            raise ValueError("state-dir must be outside the workspace")
        resolved_state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        run_guard = RunGuard()
        bound = lifecycle or RuntimeLifecycle.create(is_busy=lambda: run_guard.busy)
        bound.attach(run_guard)

        return cls(
            agent=agent or create_agent(resolved_workspace),
            context_store=ContextStore(resolved_state_dir / CONTEXT_FILENAME),
            transcript=AppendLog(resolved_state_dir / TRANSCRIPT_FILENAME, payload_key="message"),
            ui_events=AppendLog(resolved_state_dir / UI_EVENTS_FILENAME, payload_key="event"),
            run_guard=run_guard,
            lifecycle=bound,
        )


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents
