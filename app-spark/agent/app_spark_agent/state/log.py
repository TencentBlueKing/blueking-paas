"""Append-only JSONL storage for one conversation channel.

目前主要被用来存储两类日志类持久化状态：

- message：对话的每一条原始信息
- event：AG-UI 协议的 UI 层 Client 对话
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from app_spark_agent.state.signal import ChangeSignal
from app_spark_agent.utils import append_durably, truncate_durably

_RECORD_FIELDS = ("seq", "run_id", "timestamp")


class AppendLogError(RuntimeError):
    """Raised when an append-only log cannot be read or extended."""


class LogRecord(BaseModel):
    """One immutable entry in an append-only channel.

    The body is the one field whose stored name differs, because it is chosen per channel;
    :func:`_record_model` binds it. The base class only exists to name the shape.

    :param seq: 记录日志条目时的递增序列
    :param run_id: pydantic Agent 对象每次 run 的 ID
    :param timestamp: 日志产生时的时间戳
    :param payload: 日志具体内容
    """

    # ``payload`` is aliased in the generated subclass, which is what both halves of this config
    # are for: ``populate_by_name`` so :meth:`AppendLog.append` can still pass ``payload=``, and
    # the split validation/serialization aliases so a type checker keeps seeing that keyword.
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True, frozen=True)

    seq: int = Field(gt=0)
    run_id: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    payload: Any = Field(validation_alias="payload", serialization_alias="payload")


@cache
def _record_model(payload_key: str) -> type[LogRecord]:
    """Return the record model whose body is stored under ``payload_key``.

    The key is per channel (``message`` for the model transcript, ``event`` for AG-UI events).
    """
    return create_model(
        f"LogRecord[{payload_key}]",
        __base__=LogRecord,
        payload=(
            Any,
            Field(validation_alias=payload_key, serialization_alias=payload_key),
        ),
    )


@dataclass(frozen=True)
class LogPage:
    """One batch read straight out of the channel file, plus where to resume reading.

    :param records: The entries that were read, in sequence order.
    :param next_offset: Byte offset the next batch starts at.
    """

    records: list[LogRecord]
    next_offset: int


class AppendLog:
    """Crash-safe append-only JSONL channel for one conversation.

    Entries are never rewritten and their ``seq`` is contiguous from ``base_seq + 1``, so the
    control plane can drain the channel with a single cursor. An append is one write of whole
    lines, which makes a trailing partial line unambiguous: it can only be an interrupted
    append, so it is truncated on load instead of failing the Runtime.

    :param path: JSONL file backing this channel; created on first append.
    :param payload_key: Field name the entry body is stored under.
    :param base_seq: Sequence number this file's first entry follows. Non-zero only for a
        Runtime that was cold-started into the middle of a conversation another Runtime began,
        so the numbering continues instead of restarting and colliding.
    :param signal: Flag raised after every durable append, for whoever replicates the channel.
    """

    def __init__(
        self,
        path: Path,
        *,
        payload_key: str,
        base_seq: int = 0,
        signal: ChangeSignal | None = None,
    ) -> None:
        if payload_key in _RECORD_FIELDS:
            raise AppendLogError(f"payload_key cannot shadow a record field: {payload_key}")
        if base_seq < 0:
            raise AppendLogError("base_seq must be a non-negative integer")
        self.path = path
        self.payload_key = payload_key
        self._record = _record_model(payload_key)
        self._lock = asyncio.Lock()
        self._signal = signal or ChangeSignal()
        self._base_seq = base_seq
        self._last_seq = base_seq
        self._run_ids: set[str] = set()
        self._load()

    @property
    def base_seq(self) -> int:
        """Return the sequence number this file's first entry follows."""
        return self._base_seq

    @property
    def last_seq(self) -> int:
        """Return the sequence number of the last durable entry, or the base when empty."""
        return self._last_seq

    @property
    def is_empty(self) -> bool:
        """Return whether this file holds no entries of its own yet."""
        return self._last_seq == self._base_seq

    def rebase(self, base_seq: int) -> None:
        """Renumber an untouched channel so it continues a history another Runtime wrote.

        Only legal while the channel is empty. Rebasing a channel that already holds entries
        would leave the file's own sequence numbers describing a different history than the
        one the control plane has, which is unrecoverable rather than merely wrong.

        :param base_seq: Sequence number the first entry should follow.
        :raises AppendLogError: If the channel already holds entries, or ``base_seq`` is
            negative.
        """
        if base_seq < 0:
            raise AppendLogError("base_seq must be a non-negative integer")
        if not self.is_empty:
            raise AppendLogError(
                f"{self.path.name} already holds entries up to seq {self._last_seq} and cannot be rebased"
            )
        self._base_seq = base_seq
        self._last_seq = base_seq

    def has_run(self, run_id: str) -> bool:
        """Return whether any entry was ever recorded for ``run_id``.

        This is the durable replay check: unlike the conversation context, the log is never
        rewritten by compaction, so a run that has been committed stays detectable forever --
        for as long as this file exists. A Runtime cold-started from an archived context starts
        an empty file and therefore cannot recognize a run its predecessor committed; the
        control plane mints a fresh run id per turn, so nothing relies on it doing so.
        """
        return run_id in self._run_ids

    async def append(self, run_id: str, payloads: Sequence[object]) -> int:
        """Durably append ``payloads`` as consecutive entries and return the new last sequence."""
        if not payloads:
            return self._last_seq
        async with self._lock:
            timestamp = datetime.now(UTC).isoformat()
            seq = self._last_seq
            lines: list[bytes] = []
            for payload in payloads:
                seq += 1
                record = self._record(
                    seq=seq,
                    run_id=run_id,
                    timestamp=timestamp,
                    payload=payload,
                )
                lines.append(record.model_dump_json(by_alias=True).encode() + b"\n")
            # INFO: 也许可以考虑用 https://github.com/mosquito/aiofile 替换
            await asyncio.to_thread(append_durably, self.path, b"".join(lines))
            self._last_seq = seq
            self._run_ids.add(run_id)
            # Raised only once the bytes are durable, so a replicator that reacts to it can
            # never be pointed at entries a crash would take back.
            self._signal.notify()
            return seq

    def read_since(self, since: int, limit: int) -> list[LogRecord]:
        """Return up to ``limit`` entries with a sequence number greater than ``since``.

        The file is re-read rather than mirrored in memory: the raw transcript is the largest of
        the three streams and draining it is a rare control-plane call, so paying the read is
        preferable to holding an uncompacted conversation in RAM for the process's whole life.
        """
        if since < 0:
            raise AppendLogError("since must be a non-negative integer")
        if limit <= 0:
            raise AppendLogError("limit must be a positive integer")
        if since >= self._last_seq or not self.path.exists():
            return []

        records: list[LogRecord] = []
        with self.path.open("rb") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = self._decode(line, f"line {number}")
                if record.seq <= since:
                    continue
                records.append(record)
                if len(records) == limit:
                    break
        return records

    def read_from(self, offset: int, limit: int) -> LogPage:
        """Return up to ``limit`` entries starting at byte ``offset``, and where they end.

        The cursor-based :meth:`read_since` re-reads the file from the start on every call,
        which is the right trade for the control plane's occasional drain but the wrong one for
        a replicator that walks the whole channel batch by batch: that would be quadratic in a
        transcript which can reach tens of megabytes. A byte offset is exact and stable here
        precisely because the file is append-only and an append writes whole lines, so an
        offset handed back by an earlier call still names the same line boundary.

        :param offset: Byte offset of the first entry to read; must be a line boundary, which
            is guaranteed for ``0`` and for any :attr:`LogPage.next_offset`.
        :param limit: Maximum number of entries to return.
        :return: The entries read and the offset to resume from.
        :raises AppendLogError: If the arguments are invalid or the file cannot be read.
        """
        if offset < 0:
            raise AppendLogError("offset must be a non-negative integer")
        if limit <= 0:
            raise AppendLogError("limit must be a positive integer")
        if not self.path.exists():
            return LogPage(records=[], next_offset=offset)

        records: list[LogRecord] = []
        position = offset
        try:
            with self.path.open("rb") as handle:
                handle.seek(offset)
                for line in handle:
                    # A torn tail is only reachable by a reader racing an append in progress,
                    # since `_load` truncates one at startup. Stopping short of it leaves the
                    # offset on the last whole line, so the next call picks the entry up once
                    # its bytes are complete.
                    if not line.endswith(b"\n"):
                        break
                    position += len(line)
                    if not line.strip():
                        continue
                    records.append(self._decode(line, f"offset {position - len(line)}"))
                    if len(records) == limit:
                        break
        except OSError as exc:
            raise AppendLogError(f"unable to read {self.path.name}: {exc}") from exc
        return LogPage(records=records, next_offset=position)

    def offset_after(self, seq: int) -> int:
        """Return the byte offset just past the entry numbered ``seq``.

        This is how a replicator turns a persisted sequence cursor back into a byte offset once
        per process, so nothing has to store the offset itself and risk it disagreeing with the
        file. No entry is parsed: ``seq`` is contiguous from :attr:`base_seq` (``_load``
        enforces it), so the entry's position is simply how many lines precede it.

        :param seq: Sequence number to seek past; anything at or below the base returns ``0``.
        :return: Byte offset the following entry starts at.
        :raises AppendLogError: If the file cannot be read.
        """
        wanted = seq - self._base_seq
        if wanted <= 0 or not self.path.exists():
            return 0

        position = 0
        seen = 0
        try:
            with self.path.open("rb") as handle:
                for line in handle:
                    if not line.endswith(b"\n"):
                        break
                    position += len(line)
                    if not line.strip():
                        continue
                    seen += 1
                    if seen == wanted:
                        break
        except OSError as exc:
            raise AppendLogError(f"unable to read {self.path.name}: {exc}") from exc
        return position

    def dump(self, records: Sequence[LogRecord]) -> list[dict[str, object]]:
        """Return the JSON-compatible wire representation of ``records``."""
        return [record.model_dump(mode="json", by_alias=True) for record in records]

    def _load(self) -> None:
        """Recover the cursor and the run index by replaying the file one line at a time.

        Streamed rather than read whole: a long conversation's transcript is unbounded, while
        all this pass keeps is a sequence number and a set of run ids. Peak memory is therefore
        one line instead of the entire channel.
        """
        if not self.path.exists():
            return

        # Bytes belonging to lines that were fully written; anything past it is a torn tail.
        durable = 0
        interrupted = False
        try:
            with self.path.open("rb") as handle:
                for number, line in enumerate(handle, start=1):
                    # Only the very last line can lack its terminator, and only an append that
                    # never finished can have left it that way: appends write whole lines.
                    if not line.endswith(b"\n"):
                        interrupted = True
                        break
                    durable += len(line)
                    if not line.strip():
                        continue
                    record = self._decode(line, f"line {number}")
                    if record.seq != self._last_seq + 1:
                        raise AppendLogError(f"{self.path.name} line {number}: seq {record.seq} is not contiguous")
                    self._last_seq = record.seq
                    self._run_ids.add(record.run_id)
        except OSError as exc:
            raise AppendLogError(f"unable to read {self.path.name}: {exc}") from exc

        if interrupted:
            self._truncate(durable)

    def _decode(self, line: bytes, where: str) -> LogRecord:
        """Structure one stored line, naming ``where`` it was found if it cannot be read.

        The locator is a caller-formatted string rather than a line number because the two
        readers find entries by different means: :meth:`_load` and :meth:`read_since` walk
        lines, while :meth:`read_from` starts at a byte offset and never learns a line number.
        """
        try:
            return self._record.model_validate_json(line)
        except ValidationError as exc:
            raise AppendLogError(f"{self.path.name} {where}: invalid entry: {exc}") from exc

    def _truncate(self, size: int) -> None:
        try:
            truncate_durably(self.path, size)
        except OSError as exc:
            raise AppendLogError(f"unable to discard the interrupted tail of {self.path.name}: {exc}") from exc
