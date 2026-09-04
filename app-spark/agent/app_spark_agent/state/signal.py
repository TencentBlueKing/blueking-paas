"""The wake-up flag that connects the durable state to whoever replicates it.

Kept here rather than in :mod:`app_spark_agent.replication` because the state channels are the
ones that raise it, and a channel must not have to import its own observer to be able to say
"something changed". A Runtime with no control plane configured still builds one; setting a
flag nobody waits on costs nothing, and it keeps every call site free of a ``None`` check.
"""

from __future__ import annotations

import asyncio


class ChangeSignal:
    """A collapsing "something was committed" flag.

    Deliberately one flag for all three channels rather than one per channel: the only consumer
    asks "is there anything to push", and waiting on three separate events would mean juggling
    three tasks to answer a question that has a single answer.

    Collapsing means a burst of appends wakes the consumer once, which is the intent -- it
    re-reads the cursors when it wakes, so it always sees the whole burst.

    Example::

        signal = ChangeSignal()
        log = AppendLog(path, payload_key="message", signal=signal)

        # In the replicator's loop:
        await signal.wait()
        signal.clear()  # cleared before draining, so appends during a drain wake it again
    """

    def __init__(self) -> None:
        # Constructed outside a running loop: `asyncio.Event` has not bound a loop at creation
        # time since Python 3.10, and the state channels build their own locks the same way.
        self._event = asyncio.Event()

    @property
    def raised(self) -> bool:
        """Return whether a change has been signalled and not yet consumed."""
        return self._event.is_set()

    def notify(self) -> None:
        """Announce that durable state changed."""
        self._event.set()

    def clear(self) -> None:
        """Consume the flag.

        Must be called *before* reading the cursors it refers to, never after: clearing after a
        drain would discard an append that landed while the drain was in flight.
        """
        self._event.clear()

    async def wait(self) -> None:
        """Block until the flag is raised, returning at once when it already is."""
        await self._event.wait()
