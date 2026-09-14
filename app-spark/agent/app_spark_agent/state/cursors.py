"""Sequence bookkeeping that has to outlive a single Runtime incarnation.

Two questions are answered by one document, because both are "where does this channel sit
relative to the conversation as a whole", and both are read at startup before anything else:

- ``base_seq`` -- the sequence number this incarnation's channel *continues from*. A Runtime
  cold-started from an archived context begins with empty log files, but the conversation's
  history already reached, say, seq 40 on the control plane. Numbering the new file from 1
  would collide with it, so the restore seeds a base and the first append becomes 41.
- ``pushed_seq`` -- how far replication has got. Only the sequence number is stored, never a
  byte offset: an offset can be recomputed exactly by scanning the append-only file once per
  process, and storing it would create a second truth that can disagree with the file.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app_spark_agent.utils import write_atomic

# Bumped only together with the payload model below.
CURSORS_SCHEMA_VERSION: Literal[1] = 1


class CursorStateError(RuntimeError):
    """Raised when the persisted cursors are invalid or cannot be replaced."""


class Channel(StrEnum):
    """An append-only channel, named the way the control plane names it.

    Distinct from :attr:`~app_spark_agent.state.log.AppendLog.payload_key`, which names the
    field an entry's body is stored *under* (``message`` / ``event``). The two happen to
    coincide for the transcript and deliberately do not for the UI events, whose channel is
    ``ui_event`` everywhere outside the record body.
    """

    MESSAGE = "message"
    UI_EVENT = "ui_event"


class ChannelCursor(BaseModel):
    """Where one append-only channel starts and how far it has been replicated.

    :param base_seq: Sequence number the channel's first local entry follows.
    :param pushed_seq: Last sequence number the control plane has acknowledged.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    base_seq: int = Field(default=0, ge=0)
    pushed_seq: int = Field(default=0, ge=0)


class CursorsPayload(BaseModel):
    """The versioned document the cursors are persisted as.

    Split from the store for the same reason :class:`~app_spark_agent.state.context.
    ContextPayload` is: this describes what a readable document must contain, starting with the
    ``schema_version`` that decides whether it can be read at all.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    channels: dict[Channel, ChannelCursor] = Field(default_factory=dict[Channel, ChannelCursor])
    pushed_context_version: int = Field(default=0, ge=0)


class CursorStore:
    """Atomically replace the cursor document of one Runtime process.

    The whole document is rewritten on every change. That is affordable because it is a handful
    of integers, and it means a reader can never observe a half-updated set of cursors -- which
    matters, since a base and a push position that disagree would make the channel unreadable.

    Example::

        cursors = CursorStore(state_dir / "cursors.json")
        await cursors.rebase({Channel.MESSAGE: 40, Channel.UI_EVENT: 55})
        await cursors.record_push(Channel.MESSAGE, seq=41)

    :param path: JSON document backing the cursors; created on first write.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._payload = self._load()

    @property
    def pushed_context_version(self) -> int:
        """Return the context version the control plane has acknowledged."""
        return self._payload.pushed_context_version

    def channel(self, channel: Channel) -> ChannelCursor:
        """Return one channel's cursor, defaulting to the start of a fresh conversation."""
        return self._payload.channels.get(channel, ChannelCursor())

    async def rebase(self, bases: Mapping[Channel, int]) -> None:
        """Record the sequence numbers the named channels continue from.

        Also moves each channel's ``pushed_seq`` up to its new base: everything up to the base
        is by definition already on the control plane, since the base came from there.

        :param bases: New base sequence number per channel.
        :raises CursorStateError: If the document cannot be written.
        """
        async with self._lock:
            channels = dict(self._payload.channels)
            for channel, base_seq in bases.items():
                current = channels.get(channel, ChannelCursor())
                channels[channel] = ChannelCursor(
                    base_seq=base_seq,
                    pushed_seq=max(current.pushed_seq, base_seq),
                )
            await self._persist(self._payload.model_copy(update={"channels": channels}))

    async def record_push(self, channel: Channel, *, seq: int) -> None:
        """Record that the control plane has accepted ``channel`` up to ``seq``.

        Never moves a cursor backwards, so a retry that re-sends an already-accepted batch
        cannot undo progress.

        :param channel: Channel that was replicated.
        :param seq: Last sequence number the control plane acknowledged.
        :raises CursorStateError: If the document cannot be written.
        """
        async with self._lock:
            current = self.channel(channel)
            if seq <= current.pushed_seq:
                return
            channels = dict(self._payload.channels)
            channels[channel] = current.model_copy(update={"pushed_seq": seq})
            await self._persist(self._payload.model_copy(update={"channels": channels}))

    async def record_context_push(self, version: int) -> None:
        """Record that the control plane holds the context at ``version``.

        :param version: Context version the control plane acknowledged.
        :raises CursorStateError: If the document cannot be written.
        """
        async with self._lock:
            if version <= self._payload.pushed_context_version:
                return
            await self._persist(self._payload.model_copy(update={"pushed_context_version": version}))

    async def _persist(self, payload: CursorsPayload) -> None:
        try:
            await asyncio.to_thread(write_atomic, self.path, payload.model_dump_json().encode())
        except OSError as exc:
            raise CursorStateError(f"unable to write {self.path.name}: {exc}") from exc
        self._payload = payload

    def _load(self) -> CursorsPayload:
        if not self.path.exists():
            return CursorsPayload(schema_version=CURSORS_SCHEMA_VERSION)
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise CursorStateError(f"unable to read {self.path.name}: {exc}") from exc
        try:
            return CursorsPayload.model_validate_json(raw)
        except ValidationError as exc:
            raise CursorStateError(f"invalid cursor document {self.path.name}: {exc}") from exc
