"""Running a turn as a task of its own, so that it outlives the request that started it.

A turn used to be driven by the SSE response body: the model ran for exactly as long as someone
was reading. A browser that reloaded, or a network blip anywhere between it and this process,
cancelled the generator and with it the run -- half a turn of tool calls, no committed context,
and an "interrupted" commit nobody asked for.

So the run is a task this module owns, and the response is only a subscriber to what it emits.
A subscriber that goes away stops reading and nothing else. Stopping a turn is an explicit
request instead (:meth:`RunSupervisor.request_stop`), delivered through pydantic-ai's own
cancellation so that the turn still ends the way a finished one does: a closed event stream, a
committed context, a commit of whatever files it had touched.

This module knows nothing about HTTP, Git or replication. What has to happen once a turn is over
is handed in by the caller as ``finish``.
"""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.tools import RunContext

# Imported under a different name, as in routes: these lines carry run ids and error messages, and
# only this logger masks credentials and labels them with the session.
from app_spark_agent.observability import log as logger


class RuntimeClosingError(RuntimeError):
    """Raised when a run would start after shutdown has already stopped the one in progress."""


class RunStopper(AbstractCapability[Any]):
    """Let code outside the agent ask one run to stop.

    pydantic-ai can only be asked to cancel through the run's own context, which exists only once
    the run has started. A stop that arrives before that is remembered and delivered as soon as
    the context appears, so there is no window in which a request is silently lost.

    The cancellation is pydantic-ai's first-party one, not ``Task.cancel()``. That difference is
    the point: it ends in ``RunCancelled``, which the AG-UI stream closes out properly and whose
    messages can still be committed as the conversation's context.
    """

    def __init__(self) -> None:
        self._ctx: RunContext[Any] | None = None
        self._requested = False

    @property
    def requested(self) -> bool:
        """Return whether anyone has asked this run to stop."""
        return self._requested

    async def before_run(self, ctx: RunContext[Any]) -> None:
        """Capture the run's context, and deliver a stop that came in before it existed."""
        self._ctx = ctx
        if self._requested:
            ctx.cancel()

    def request(self) -> None:
        """Ask the run to stop. Idempotent, and a no-op once the run has finished."""
        self._requested = True
        if self._ctx is not None:
            self._ctx.cancel()


class RunEvents:
    """The encoded SSE chunks of one run, kept for as long as the run is referenced.

    There is one subscriber today, the response that started the run, and it is always late: the
    task is running before that response is even returned, let alone iterated, so the first
    chunks exist before anyone reads them. Every subscriber therefore starts from the first chunk.

    Nothing is trimmed once read. Trimming would buy little -- one turn's events are kilobytes to
    a few megabytes, and they go when the run does -- and would make "from the first chunk" true
    only for the first subscriber, which a reconnecting one would then silently not get.
    """

    def __init__(self) -> None:
        self._chunks: list[str] = []
        self._closed = False
        # Replaced on every change rather than cleared: a subscriber waits on the event that was
        # current when it found nothing new, and must be woken by the very next change.
        self._changed = asyncio.Event()

    def append(self, chunk: str) -> None:
        """Add one chunk and wake every waiting subscriber."""
        self._chunks.append(chunk)
        self._notify()

    def close(self) -> None:
        """Mark the stream complete. Subscribers end once they have read everything."""
        self._closed = True
        self._notify()

    async def subscribe(self) -> AsyncIterator[str]:
        """Yield every chunk from the first, then follow new ones until the stream closes."""
        sent = 0
        while True:
            while sent < len(self._chunks):
                yield self._chunks[sent]
                sent += 1
            if self._closed:
                return
            await self._changed.wait()

    def _notify(self) -> None:
        changed, self._changed = self._changed, asyncio.Event()
        changed.set()


@dataclass(frozen=True)
class ActiveRun:
    """One run in progress: its identity, what it has emitted, and the task driving it."""

    run_id: str
    events: RunEvents
    stopper: RunStopper
    task: asyncio.Task[None]


class RunSupervisor:
    """Own the run in progress, if there is one.

    The run guard already makes sure there is at most one; this holds on to it, because a task
    nobody references can be garbage-collected mid-run, and because a stop request and a
    shutdown both need to find it again.
    """

    def __init__(self) -> None:
        self._current: ActiveRun | None = None
        self._closing = False

    @property
    def current(self) -> ActiveRun | None:
        """Return the run in progress, or ``None``."""
        return self._current

    @property
    def closing(self) -> bool:
        """Return whether the process is shutting down.

        A run winding down then should not wait on the network: shutdown drains the state
        itself, against a deadline of its own.
        """
        return self._closing

    def start(
        self,
        *,
        run_id: str,
        stopper: RunStopper,
        events: AsyncIterator[str],
        finish: Callable[[bool], Awaitable[None]],
        release: Callable[[], None],
        record_error: Callable[[str], Awaitable[str]],
    ) -> ActiveRun:
        """Start driving one run, and return it with the task already scheduled.

        Started before the caller returns its response, so that a client which hangs up during
        the handshake still leaves a turn that runs to its end.

        Example::

            run = supervisor.start(run_id=..., stopper=stopper, events=encoded, finish=finish,
                                   release=lease.release, record_error=end_with_error)
            return StreamingResponse(run.events.subscribe(), media_type="text/event-stream")

        :param run_id: The run's identifier, as the client chose it.
        :param stopper: The capability the run was given, so it can be asked to stop.
        :param events: The run's encoded SSE chunks. Driving this iterator is running the turn.
        :param finish: Called once the events are over, with whether the event stream ran to its
            end rather than being broken off. Saving the workspace and flushing state goes here.
        :param release: Hands the run guard back. Called after ``finish``, and always.
        :param record_error: Records a failure that broke the event stream itself, wherever the
            run's events are kept, and returns it encoded as a final chunk -- so that neither a
            subscriber nor a later replay sees a run that just stopped. Must not raise.
        :return: The run now in progress.
        :raises RuntimeClosingError: If shutdown has begun. A run admitted just before it, still
            preparing when the run in progress was stopped, would otherwise start afterwards and
            be cut off with no wind-down at all.
        """
        if self._closing:
            raise RuntimeClosingError("The Agent Runtime is shutting down.")
        buffered = RunEvents()
        task = asyncio.create_task(
            self._drive(
                run_id=run_id,
                source=events,
                sink=buffered,
                finish=finish,
                release=release,
                record_error=record_error,
            ),
            name=f"run-{run_id}",
        )
        run = ActiveRun(run_id=run_id, events=buffered, stopper=stopper, task=task)
        self._current = run
        return run

    def request_stop(self, run_id: str) -> bool:
        """Ask the run in progress to stop, if it is the one named.

        :param run_id: Run the caller means. A stale id must not stop the turn after it.
        :return: Whether ``run_id`` is the run in progress. ``True`` again on a repeated request.
        """
        run = self._current
        if run is None or run.run_id != run_id:
            return False
        run.stopper.request()
        return True

    async def aclose(self, *, stop_timeout_seconds: float, wind_down_timeout_seconds: float) -> None:
        """Stop the run in progress, if any, and wait a bounded time for it to finish winding down.

        Asked politely first, so the turn's context still gets committed. A run that does not
        stop within the bound is cancelled outright, and still winds down: ``finish`` runs either
        way, it only loses the context commit.

        Cancelling does not end a task, it only interrupts it once: the wind-down that follows is
        ordinary awaits again, and the workspace commit in it queues behind any push the
        background saver has in flight. That is why the wind-down has a bound of its own. A run
        still winding down past it is left running, not cancelled a second time -- the commit is
        shielded and holds the Git lock, so it stays consistent whether anyone awaits it or not --
        and shutdown carries on to the drain, which still has the state to hand over.

        :param stop_timeout_seconds: How long the polite stop gets before the task is cancelled.
        :param wind_down_timeout_seconds: How long a cancelled run then gets to wind down.
        """
        self._closing = True
        run = self._current
        if run is None:
            return
        run.stopper.request()
        if await _settled(run.task, timeout_seconds=stop_timeout_seconds):
            return
        logger.warning(
            "run %s did not stop within %.0fs, cancelling it; its context will not be committed",
            run.run_id,
            stop_timeout_seconds,
        )
        run.task.cancel()
        if not await _settled(run.task, timeout_seconds=wind_down_timeout_seconds):
            logger.warning(
                "run %s was still winding down %.0fs after being cancelled; shutting down without "
                "waiting for it, so its files may not be part of what gets handed over",
                run.run_id,
                wind_down_timeout_seconds,
            )

    async def _drive(
        self,
        *,
        run_id: str,
        source: AsyncIterator[str],
        sink: RunEvents,
        finish: Callable[[bool], Awaitable[None]],
        release: Callable[[], None],
        record_error: Callable[[str], Awaitable[str]],
    ) -> None:
        completed = False
        try:
            try:
                async for chunk in source:
                    sink.append(chunk)
            finally:
                # When this loop is left early, pydantic-ai's own run task has to be torn down
                # now, not whenever the generator happens to be collected.
                if isinstance(source, AsyncGenerator):
                    await source.aclose()
            # Only says the stream was not broken off. A stopped turn ends its stream normally
            # too, so whether it got to finish is for ``finish`` to combine with what the agent
            # reported; whether the model succeeded is the transcript's to tell.
            completed = True
        except Exception as exc:  # noqa: BLE001
            # pydantic-ai turns model and tool failures into events of their own. Reaching here
            # means the stream itself broke, e.g. the AG-UI log could not be written.
            logger.exception("the event stream of run %s broke", run_id)
            sink.append(await record_error(f"The Agent Runtime could not continue this run: {exc}"))
        finally:
            try:
                await finish(completed)
            except Exception:  # noqa: BLE001
                # Nobody awaits this task, so an exception left to escape would only ever show up
                # as "never retrieved". The run guard must be handed back regardless.
                logger.exception("run %s could not be wound down cleanly", run_id)
            finally:
                release()
                if self._current is not None and self._current.run_id == run_id:
                    self._current = None
                # Last, so that a subscriber seeing the stream end can rely on /health already
                # reporting the Runtime as idle.
                sink.close()
                logger.info("run stream closed run_id=%s stream_completed=%s", run_id, completed)


async def _settled(task: asyncio.Task[None], *, timeout_seconds: float) -> bool:
    """Wait up to a bound for ``task`` to finish, without cancelling it when the bound passes."""
    done, _ = await asyncio.wait({task}, timeout=timeout_seconds)
    return bool(done)
