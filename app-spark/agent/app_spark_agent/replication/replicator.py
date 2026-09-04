"""Mirroring this Runtime's durable state onto the control plane.

The design point is that the local files stay the outbox. They already are one: an append is
fsynced whole lines at a time, ``seq`` is contiguous, a torn tail is truncated on load, and
:meth:`~app_spark_agent.state.log.AppendLog.read_from` reads a batch from a byte offset. The
only thing a queue would have added is a durable record of how far the push has got, and that
is what :class:`~app_spark_agent.state.cursors.CursorStore` is. Keeping a second copy of every
message in a local database would buy nothing and cost a second fsync on the model round-trip
path, where every append happens.

So the Runtime never blocks a run on the network: it commits locally, raises a flag, and this
task catches up behind it. What makes that safe rather than merely fast is the barrier at the
end of a run -- :meth:`StateReplicator.flush` -- which is where a turn stops being "durable
here" and becomes "durable on the control plane".
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from app_spark_agent import settings
from app_spark_agent.replication.client import ControlPlaneClient, ControlPlaneError
from app_spark_agent.state import (
    AppendLog,
    AppendLogError,
    ChangeSignal,
    Channel,
    ContextStore,
    CursorStateError,
    CursorStore,
)

logger = logging.getLogger(__name__)

# Everything a drain pass can fail with that is worth retrying rather than crashing the task.
# Deliberately narrow: a bug in this module should surface as a traceback, not as silent lag.
_RECOVERABLE = (ControlPlaneError, AppendLogError, CursorStateError)

# How many times one channel may rewind within a single drain pass. A rewind means the control
# plane held less than it just accepted, and one re-send is what repairs that. A channel that
# keeps rewinding is talking to a control plane that is dropping what it accepts, so re-sending
# in a tight loop would spin instead of converging -- better to fail the pass and let the
# backoff decide when to try again.
_MAX_REWINDS_PER_PASS = 2


class StateReplicator:
    """Push the three durable channels to the control plane, behind the run.

    Example::

        replicator = StateReplicator(
            client=ControlPlaneClient(base_url=..., token=...),
            cursors=runtime.cursors,
            signal=runtime.signal,
            channels={Channel.MESSAGE: runtime.transcript},
            context_store=runtime.context_store,
        )
        await replicator.start()
        ...
        await replicator.flush(timeout_seconds=30.0)
        await replicator.aclose()

    :param client: Where the state is pushed.
    :param cursors: Durable record of how far each channel has been pushed.
    :param signal: Flag the state channels raise when they commit something new.
    :param channels: The append-only channels to replicate, by the name the control plane
        knows them under.
    :param context_store: The mutable context, replicated as a whole document.
    :param batch_size: Maximum entries per ingest call.
    :param retry_backoff_seconds: How long to wait after a failed pass before trying again.
    """

    def __init__(
        self,
        *,
        client: ControlPlaneClient,
        cursors: CursorStore,
        signal: ChangeSignal,
        channels: Mapping[Channel, AppendLog],
        context_store: ContextStore,
        batch_size: int | None = None,
        retry_backoff_seconds: float | None = None,
    ) -> None:
        self._client = client
        self._cursors = cursors
        self._signal = signal
        self._channels = dict(channels)
        self._context_store = context_store
        self._batch_size = batch_size if batch_size is not None else settings.PUSH_BATCH_SIZE
        self._retry_backoff_seconds = (
            retry_backoff_seconds if retry_backoff_seconds is not None else settings.PUSH_RETRY_BACKOFF_SECONDS
        )
        # Byte offset each channel's next batch starts at, resolved from the durable sequence
        # cursor on first use. Held only in memory: the file is the truth, and re-deriving an
        # offset costs one scan per process instead of risking a stored offset that disagrees.
        self._offsets: dict[Channel, int] = {}
        # Serializes the background pass against an end-of-run flush, so the two cannot send
        # overlapping batches of the same channel and race each other's cursor writes.
        self._drain_lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    @property
    def pushed_context_version(self) -> int:
        """Return the context version the control plane is known to hold."""
        return self._cursors.pushed_context_version

    def pushed_seq(self, channel: Channel) -> int:
        """Return the last sequence number the control plane is known to hold."""
        return self._cursors.channel(channel).pushed_seq

    async def start(self) -> None:
        """Begin replicating in the background.

        Signals itself once, because a Runtime reopening a state directory may already hold
        entries an earlier incarnation never managed to push, and nothing else would wake it
        until the conversation happened to continue.
        """
        if self._task is not None:
            return
        self._signal.notify()
        self._task = asyncio.create_task(self._loop(), name="state-replicator")

    async def aclose(self) -> None:
        """Stop replicating and release the connection pool.

        Does not flush: the caller decides whether a shutdown should wait for the control plane
        (see :meth:`flush`), because that answer differs between a crash and an orderly stop.
        """
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            # The task only ever exits by cancellation, so this both reaps it and keeps the
            # event loop from reporting it as never retrieved.
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()

    async def flush(self, *, timeout_seconds: float) -> bool:
        """Push everything outstanding now and report whether the control plane caught up.

        This is the barrier that makes the state directory disposable: once it returns ``True``
        the turn survives losing this Runtime entirely. A ``False`` deliberately does *not*
        fail the run -- the entries are still in the local files and the background task keeps
        retrying -- but it does mean the control plane is behind, which the caller should make
        visible rather than swallow.

        The answer is decided by comparing cursors after the pass, not by "the pass raised
        nothing". A drain can finish cleanly and still be behind -- an append that lands
        mid-drain is the ordinary case -- and reporting that as success is exactly the claim
        that would strand a turn on a Runtime about to be thrown away.

        :param timeout_seconds: How long to keep trying before giving up on this attempt.
        :return: Whether every channel is now replicated.
        """
        try:
            async with asyncio.timeout(timeout_seconds):
                async with self._drain_lock:
                    # Cleared before draining, never after: an append that lands mid-drain has
                    # to leave the flag raised for the background task to pick up.
                    self._signal.clear()
                    await self._drain_all()
        except (TimeoutError, *_RECOVERABLE) as exc:
            logger.warning("the control plane is behind after a flush attempt: %s", exc)
            self._signal.notify()
            return False

        outstanding = self.outstanding()
        if not outstanding:
            return True
        # Drained without error and still behind. Raise the flag before reporting it: nothing
        # else will, and an idle conversation has no next append to wake the background task.
        logger.warning("the control plane is still behind after a clean flush: %s", outstanding)
        self._signal.notify()
        return False

    def outstanding(self) -> dict[str, str]:
        """Describe what the control plane is still missing, empty when it holds everything.

        A description rather than a bool because both callers need the detail: the log line in
        :meth:`flush` has to say *what* is behind, and a control plane reporting replication lag
        to its own clients should not have to re-derive it.

        :return: One entry per channel that is behind, keyed by the channel's name.
        """
        behind: dict[str, str] = {}
        for channel, log in self._channels.items():
            pushed = self._cursors.channel(channel).pushed_seq
            if pushed < log.last_seq:
                behind[str(channel)] = f"pushed seq {pushed} of {log.last_seq}"
        version = self._context_store.context.context_version
        pushed_version = self._cursors.pushed_context_version
        if pushed_version < version:
            behind["context"] = f"pushed version {pushed_version} of {version}"
        return behind

    async def _loop(self) -> None:
        """Drain whenever the state changes, backing off after a failed pass."""
        while True:
            await self._signal.wait()
            self._signal.clear()
            try:
                async with self._drain_lock:
                    await self._drain_all()
            except asyncio.CancelledError:
                raise
            except _RECOVERABLE as exc:
                logger.warning("replication to the control plane failed, retrying: %s", exc)
                # Raise the flag again so the next pass retries what this one left behind, then
                # wait out the backoff rather than spinning on a control plane that is down.
                self._signal.notify()
                await asyncio.sleep(self._retry_backoff_seconds)

    async def _drain_all(self) -> None:
        """Bring every channel up to date, logs before context.

        Logs go first because they are what the client's view of the conversation is rebuilt
        from, so their lag is the one a user can see. The context only matters to a cold start,
        which by definition cannot happen while this Runtime is still alive.
        """
        for channel, log in self._channels.items():
            await self._drain_channel(channel, log)
        await self._drain_context()

    async def _drain_channel(self, channel: Channel, log: AppendLog) -> None:
        """Push one channel's unsent entries, batch by batch.

        A rewind is repaired within this same loop rather than deferred. Returning early would
        leave a hole open in the middle of a channel this pass is about to report as drained,
        and for a conversation that has gone idle there is no next append to trigger a retry.
        """
        if channel not in self._offsets:
            pushed_seq = self._cursors.channel(channel).pushed_seq
            self._offsets[channel] = await asyncio.to_thread(log.offset_after, pushed_seq)

        rewinds = 0
        while True:
            page = await asyncio.to_thread(log.read_from, self._offsets[channel], self._batch_size)
            if not page.records:
                return
            sent_through = page.records[-1].seq
            acknowledged = await self._client.append(channel, log.dump(page.records))
            if acknowledged < sent_through:
                # The control plane holds less than it just accepted, so its copy of this
                # channel was truncated behind our back. Rewind to what it admits to having and
                # re-send the gap below; claiming success here would strand it.
                if acknowledged < log.base_seq:
                    # The hole is below this file's first entry, so it is in history an earlier
                    # incarnation wrote and this Runtime simply does not hold. Nothing here can
                    # repair it, and pretending otherwise would re-send the same batch forever.
                    raise ControlPlaneError(
                        f"the control plane is missing {channel} entries up to seq "
                        f"{acknowledged}, which this Runtime's log begins after (base seq "
                        f"{log.base_seq})"
                    )
                rewinds += 1
                if rewinds > _MAX_REWINDS_PER_PASS:
                    raise ControlPlaneError(
                        f"the control plane rewound {channel} {rewinds} times in one pass, "
                        f"last reporting seq {acknowledged} after accepting seq {sent_through}; "
                        "it is not keeping what it accepts"
                    )
                logger.warning(
                    "the control plane reports %s only up to seq %d after accepting seq %d; "
                    "rewinding to re-send the gap",
                    channel,
                    acknowledged,
                    sent_through,
                )
                self._offsets[channel] = await asyncio.to_thread(log.offset_after, acknowledged)
                continue
            self._offsets[channel] = page.next_offset
            await self._cursors.record_push(channel, seq=sent_through)

    async def _drain_context(self) -> None:
        """Push the context document if it has moved since the last acknowledged version.

        Coalescing rather than queueing: a run that compacts twice commits twice, but only the
        last version is worth transferring, and each one is potentially megabytes.
        """
        context = self._context_store.context
        version = context.context_version
        if version <= self._cursors.pushed_context_version:
            return
        payload: dict[str, Any] = await asyncio.to_thread(context.as_payload)
        acknowledged = await self._client.put_context(payload)
        if acknowledged < version:
            # It answered with an older version than the one just sent, so its archive is not
            # what this Runtime holds. Recording the local number would claim a cold start can
            # restore a document the control plane never took.
            #
            # Raised rather than logged and skipped: a pass that returns normally while still
            # behind is a pass nothing will retry, because the background task parks on the
            # change signal and an idle conversation raises it no further.
            raise ControlPlaneError(
                f"the control plane reports context version {acknowledged} after being sent "
                f"version {version}; it did not archive the document"
            )
        await self._cursors.record_context_push(version)
