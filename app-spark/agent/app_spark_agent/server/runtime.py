"""The live objects one Runtime process serves a single conversation from.

This module knows nothing about HTTP. It owns what the views operate on -- the three durable
state channels, the agent, and the guard that keeps runs from overlapping -- so the view layer
in :mod:`app_spark_agent.server.routes` is left with nothing but request and response handling.
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import Agent

from app_spark_agent import settings
from app_spark_agent.agent import create_agent
from app_spark_agent.app_supervisor import AppSupervisor
from app_spark_agent.git.saver import WorkspaceSaver
from app_spark_agent.launch_tool import LaunchTool
from app_spark_agent.replication import ControlPlaneClient, StateReplicator
from app_spark_agent.server.lifecycle import RuntimeLifecycle
from app_spark_agent.state import (
    AppendLog,
    ChangeSignal,
    Channel,
    ContextStore,
    ConversationContext,
    CursorStore,
)

logger = logging.getLogger(__name__)

# The on-disk names of the three state channels. Deliberately not configurable: they are the
# contract the control plane reads a state directory by, so renaming one is a migration rather
# than a deployment knob.
CONTEXT_FILENAME = "context.json"
TRANSCRIPT_FILENAME = "log.jsonl"
UI_EVENTS_FILENAME = "ui_events.jsonl"

# Where the sequence bookkeeping lives: which numbers this incarnation continues from, and how
# far replication has got. Not a fourth channel -- it is metadata *about* the three.
CURSORS_FILENAME = "cursors.json"

# How often the pre-run gate re-checks whether the previous turn has been saved. Short enough
# that a push landing does not add noticeable latency to the next turn.
_SAVE_POLL_INTERVAL_SECONDS = 0.1


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
    :param cursors: Where each channel's numbering starts and how far it has been replicated.
    :param run_guard: Guard admitting one mutating operation at a time.
    :param lifecycle: Idle timeout and the registry of application children.
    :param app_supervisor: Starts and watches the workspace application process.
    :param launch_tool: The model's way to launch that process; its per-run budget is reset by
        ``POST /runs``. Held here rather than only inside the agent because an injected agent
        does not carry one.
    :param replicator: Pushes the durable state to the control plane, or ``None`` when this
        Runtime has no control plane and its state directory is all there is.
    :param saver: Persists the workspace files to the Project's Git repository, or ``None`` when
        this Runtime has no repository configured and the workspace is local-only.
    """

    agent: Agent[Any, Any]
    context_store: ContextStore
    transcript: AppendLog
    ui_events: AppendLog
    cursors: CursorStore
    run_guard: RunGuard
    lifecycle: RuntimeLifecycle
    app_supervisor: AppSupervisor
    launch_tool: LaunchTool
    replicator: StateReplicator | None
    saver: WorkspaceSaver | None = None

    @classmethod
    def open(
        cls,
        *,
        workspace: Path,
        state_dir: Path,
        agent: Agent[Any, Any] | None = None,
        lifecycle: RuntimeLifecycle | None = None,
        control_plane: ControlPlaneClient | None = None,
        saver: WorkspaceSaver | None = None,
    ) -> ConversationRuntime:
        """Validate the two directories and open the conversation's three state channels.

        The channels are numbered from whatever the cursor document says, so a Runtime that was
        cold-started into the middle of an existing conversation continues its sequence instead
        of restarting at 1 and colliding with the history the control plane already holds.

        :param workspace: Existing directory exposed to coding tools.
        :param state_dir: Directory outside ``workspace`` holding the durable state; created
            with owner-only permissions when missing.
        :param agent: Optional preconfigured agent, primarily for embedding or for tests.
        :param lifecycle: Optional idle / SIGTERM controller; created from settings when omitted.
        :param control_plane: Where to replicate the durable state. Passed in rather than read
            from settings here, because this class is also how tests and embedders assemble a
            Runtime -- and passing a client is the only thing they need to say to opt in.
        :param saver: Where the workspace files are persisted. Passed in for the same reason as
            ``control_plane``: opting in is one argument, and the default is a local workspace.
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

        # One flag for all three channels: the replicator's only question is "is there anything
        # to push", and that has a single answer.
        signal = ChangeSignal()
        cursors = CursorStore(resolved_state_dir / CURSORS_FILENAME)
        context_store = ContextStore(resolved_state_dir / CONTEXT_FILENAME, signal=signal)
        transcript = AppendLog(
            resolved_state_dir / TRANSCRIPT_FILENAME,
            payload_key="message",
            base_seq=cursors.channel(Channel.MESSAGE).base_seq,
            signal=signal,
        )
        ui_events = AppendLog(
            resolved_state_dir / UI_EVENTS_FILENAME,
            payload_key="event",
            base_seq=cursors.channel(Channel.UI_EVENT).base_seq,
            signal=signal,
        )

        replicator = None
        if control_plane is not None:
            replicator = StateReplicator(
                client=control_plane,
                cursors=cursors,
                signal=signal,
                channels={Channel.MESSAGE: transcript, Channel.UI_EVENT: ui_events},
                context_store=context_store,
            )

        # 监督器先于 agent 构造：模型的 launch 工具是进程内直调它，不走 HTTP、不碰凭据。
        app_supervisor = AppSupervisor(resolved_workspace, bound.processes, ui_events)
        launch_tool = LaunchTool(app_supervisor)

        if not agent:
            agent = create_agent(
                resolved_workspace,
                state_dir=resolved_state_dir,
                extra_tools=[launch_tool.as_tool()],
            )

        return cls(
            agent=agent,
            context_store=context_store,
            transcript=transcript,
            ui_events=ui_events,
            cursors=cursors,
            run_guard=run_guard,
            lifecycle=bound,
            app_supervisor=app_supervisor,
            launch_tool=launch_tool,
            replicator=replicator,
            saver=saver,
        )

    async def restore(
        self,
        context: ConversationContext,
        *,
        log_seq: int,
        ui_event_seq: int,
    ) -> ConversationContext:
        """Adopt a conversation another Runtime began: its context and its numbering.

        The two halves belong together. Handing back the context without the sequence numbers
        would leave this Runtime writing entry 1 of a conversation whose entry 1 the control
        plane already has, and the control plane has no way to tell the two apart.

        Cursors are seeded before the context is written, and the seeding also marks the
        incoming context version as already replicated -- it came from the control plane, so
        pushing it straight back would upload megabytes to no effect.

        :param context: Context to adopt, as the control plane archived it.
        :param log_seq: Sequence number the transcript should continue from.
        :param ui_event_seq: Sequence number the AG-UI event history should continue from.
        :return: The adopted context.
        :raises AppendLogError: If either channel already holds entries of its own.
        :raises ConversationStateConflict: If a different context is already active.
        :raises CursorStateError: If the cursor document cannot be written.
        """
        bases = {Channel.MESSAGE: log_seq, Channel.UI_EVENT: ui_event_seq}
        # Rebased in memory first: it is the check that can legitimately fail, and failing it
        # before anything is persisted leaves the Runtime exactly as it was.
        self.transcript.rebase(log_seq)
        self.ui_events.rebase(ui_event_seq)
        await self.cursors.rebase(bases)
        await self.cursors.record_context_push(context.context_version)
        return await self.context_store.restore(context)

    async def flush_replication(self, *, timeout_seconds: float | None = None) -> bool:
        """Wait for the control plane to catch up, if there is one to catch up.

        :param timeout_seconds: How long to wait; ``None`` uses ``PUSH_FLUSH_TIMEOUT_SECONDS``.
            Shutdown passes its own, because the generous per-turn bound would there be spent
            waiting for a control plane this process will not outlive.
        :return: Whether the control plane holds everything committed so far. Always ``True``
            for a Runtime with no control plane, whose state directory is the whole story.
        """
        if self.replicator is None:
            return True
        bound = settings.PUSH_FLUSH_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        return await self.replicator.flush(timeout_seconds=bound)

    async def drain(self, *, timeout_seconds: float) -> bool:
        """Make one bounded attempt to get this Runtime's work out before the process ends.

        No ordinary path needs this: pushing is the background saver's job and a turn does not
        wait for it. Shutdown is the exception, because there is no "later" left. The workspace
        disk and the state directory are disposable by design, so a commit that only exists
        locally is a turn the user loses.

        Bounded, because being behind beats the alternative: the control plane SIGKILLs a
        Runtime that overstays its grace period, and a drain that outran that budget would be
        killed part-way through having delivered nothing at all.

        The workspace goes first and the two share one deadline rather than each getting its own
        timeout. A push is usually kilobytes while a context blob runs to megabytes, so spending
        the budget on the cheap half first is what makes it likely that both halves fit.

        :param timeout_seconds: Wall-clock bound for the whole attempt.
        :return: Whether everything reached its destination. ``False`` means this Runtime is
            being discarded while behind, which the caller should report rather than swallow.
        """
        deadline = time.monotonic() + timeout_seconds
        saved = await self._push_workspace(timeout_seconds=timeout_seconds)
        remaining = max(0.0, deadline - time.monotonic())
        caught_up = await self.flush_replication(timeout_seconds=remaining)
        return saved and caught_up

    async def _push_workspace(self, *, timeout_seconds: float) -> bool:
        """Push whatever the background saver has not, within the time given.

        Every failure means the same thing here -- the commits stayed local -- and none of them
        may stop the rest of the shutdown, so they are reported rather than raised. A push
        abandoned at the deadline may still land on the remote; that is harmless, because the
        next Runtime to open this workspace reads its position from Git rather than from any
        claim this one recorded.
        """
        if self.saver is None or not self.saver.status.outstanding:
            return True
        try:
            return await asyncio.wait_for(self.saver.push_now(), timeout=timeout_seconds)
        except TimeoutError:
            logger.warning("the workspace push did not finish within the shutdown budget")
        except Exception:
            logger.exception("the workspace could not be pushed during shutdown")
        return False

    async def save_workspace(self, *, run_id: str, conversation_id: str, completed: bool = True) -> None:
        """Commit this turn's file changes locally. Pushing happens behind the barrier.

        Deliberately does not wait for the push: see :mod:`app_spark_agent.git.saver` for why a
        network round trip does not belong at the end of a run.

        The context version is read here, at the end of the turn that produced these files, and
        travels with the commit from then on. That is the version the files go with; whatever the
        conversation is at when the push eventually lands may be a later turn's.
        """
        if self.saver is None:
            return
        await self.saver.commit_turn(
            run_id=run_id,
            conversation_id=conversation_id,
            context_version=self.context_store.context.context_version,
            completed=completed,
        )

    async def await_workspace_saved(self, *, timeout_seconds: float) -> bool:
        """Wait, up to a bound, for the previous turn's files to reach the remote.

        The bound is the escape hatch, and it is not optional: under a network partition the
        push may never land, and a Runtime that waited forever would lock the user out of their
        own conversation rather than merely failing to back it up.

        :param timeout_seconds: How long to wait; ``<= 0`` does not wait at all.
        :return: Whether the workspace is now saved remotely. ``True`` when there is no
            repository configured, where the question does not arise.
        """
        if self.saver is None:
            return True
        if not self.saver.status.outstanding:
            return True
        deadline = time.monotonic() + timeout_seconds
        while self.saver.status.outstanding and time.monotonic() < deadline:
            if not self.saver.status.retriable:
                # Waiting cannot help: this failure needs somebody to act on it.
                return False
            await asyncio.sleep(_SAVE_POLL_INTERVAL_SECONDS)
        return not self.saver.status.outstanding


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents
