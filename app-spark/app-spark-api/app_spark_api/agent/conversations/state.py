# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Keeping the authoritative copy of a conversation's state.

The Runtime pushes; this is what receives. Two properties are what the whole scheme rests on:

* Appends are idempotent. Entries are identified by their sequence number, so a batch that was
  stored but whose acknowledgement never made it back is a no-op the second time round.
* A gap is refused rather than stored. If a batch starts beyond the next expected sequence
  number, something was lost in between, and accepting it would leave a hole no later write can
  fill. Instead the batch is dropped and the true cursor is returned, which is exactly what the
  Runtime needs to rewind and re-send from the right place.
* Writes for one conversation are serialized on its row. Both properties above are read-then-
  write, so they only hold against a single writer -- and "one Runtime per conversation" is not
  something this service can actually guarantee, since a Runtime it has lost track of keeps a
  perfectly valid token. The lock is what makes the assumption true rather than hoped for.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import attrs
from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Max
from django.utils.dateparse import parse_datetime

from app_spark_api.agent.conversations.context_storage import blob_location

# `models` imports `state_models`, never this module, so this direction cannot cycle.
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.state_models import (
    ConversationContextSnapshot,
    ConversationMessage,
    ConversationUiEvent,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

# Union rather than the shared abstract base: only the concrete models have a manager and a
# `conversation` field, so this is the type that lets a query be written once for both.
ChannelModel = type[ConversationMessage] | type[ConversationUiEvent]


@attrs.frozen
class ChannelSpec:
    """How one append-only channel is stored and what its body is called on the wire.

    :param model: Table the channel's entries land in.
    :param payload_key: Field the Runtime puts the entry body under.
    """

    model: ChannelModel
    payload_key: str


# The two channels, keyed by the name the Runtime pushes them under -- that spelling is the
# wire contract, taken from the Runtime's own `Channel` enum; the tables are ours.
CHANNELS: dict[str, ChannelSpec] = {
    "message": ChannelSpec(model=ConversationMessage, payload_key="message"),
    "ui_event": ChannelSpec(model=ConversationUiEvent, payload_key="event"),
}

MESSAGE_CHANNEL = "message"
UI_EVENT_CHANNEL = "ui_event"


class ConversationStateError(Exception):
    """Raised when pushed state cannot be stored as it stands."""


def last_seq(conversation_id: Any, channel: str) -> int:
    """Return the last sequence number stored for one channel, or ``0`` when it is empty.

    :param conversation_id: Conversation to look at.
    :param channel: A key of :data:`CHANNELS`.
    :return: The channel's current cursor.
    """
    model = CHANNELS[channel].model
    highest = model.objects.filter(conversation_id=conversation_id).aggregate(Max("seq"))
    return highest["seq__max"] or 0


def append_records(
    conversation_id: Any,
    channel: str,
    records: Sequence[dict[str, Any]],
) -> int:
    """Store one pushed batch of channel entries and return the channel's resulting cursor.

    :param conversation_id: Conversation the entries belong to.
    :param channel: A key of :data:`CHANNELS`.
    :param records: Entries in the shape the Runtime's drain endpoints produce, in sequence
        order. Their sequence numbers must be contiguous.
    :return: The last sequence number now stored. Lower than the batch's own last entry when
        the batch was refused for leaving a gap, which is how the Runtime learns to rewind.
    :raises ConversationStateError: If the batch is internally inconsistent -- a caller bug, as
        opposed to the two sides having drifted apart -- or if the conversation has been deleted
        underneath the push.
    """
    spec = CHANNELS[channel]
    if not records:
        return last_seq(conversation_id, channel)

    entries = [_structure_record(spec, conversation_id, channel, raw) for raw in records]
    seqs = [entry.seq for entry in entries]
    if seqs != list(range(seqs[0], seqs[0] + len(seqs))):
        raise ConversationStateError(f"the {channel} batch is not contiguous: {seqs[0]}..{seqs[-1]}")

    with transaction.atomic():
        # 先锁会话行，再读游标。这一侧假定「一个会话同一时刻只有一个 Runtime 在写」，但那个假定
        # 并不由代码保证：LocalProcessProvider 的进程句柄只存在内存里，本服务重启之后，上一代
        # 残留的 Runtime 和新 spawn 出来的那个会拿着同样有效的 token 并发写同一个会话。
        #
        # 没有这把锁的话，下面的 Max(seq) 是无锁读：两个 writer 各自读到同一个 current，于是
        # 一批本该被接收的记录会被误判成 gap 而拒掉，Runtime 那侧则表现为反复 rewind。锁一直
        # 持有到事务提交，所以同一个会话的回写在这里排成一队。
        _lock_conversation(conversation_id)
        current = last_seq(conversation_id, channel)
        if seqs[0] > current + 1:
            # Refused, not stored. Answering with the real cursor is what lets the Runtime
            # rewind to the hole and re-send it, rather than having to guess where to restart.
            return current
        # `ignore_conflicts` is what makes a redelivered batch harmless: the unique constraint
        # on (conversation, seq) recognizes every entry that is already here.
        spec.model.objects.bulk_create(entries, ignore_conflicts=True)  # type: ignore[arg-type]
        return max(current, seqs[-1])


def read_ui_events(conversation_id: Any, *, since: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    """Return one page of stored AG-UI events, plus the channel's current cursor.

    This is the read that must not need a Runtime: opening a finished conversation should show
    its history without paying to start an agent container for it.

    :param conversation_id: Conversation to read.
    :param since: Cursor to resume from; ``0`` starts at the beginning.
    :param limit: Maximum entries to return.
    :return: The page's records in the Runtime's own wire shape, and the last stored sequence
        number.
    """
    spec = CHANNELS[UI_EVENT_CHANNEL]
    rows = ConversationUiEvent.objects.filter(
        conversation_id=conversation_id,
        seq__gt=since,
    ).order_by("seq")[:limit]
    records = [_wire_record(row, spec.payload_key) for row in rows]
    return records, last_seq(conversation_id, UI_EVENT_CHANNEL)


def save_context(conversation_id: Any, payload: dict[str, Any]) -> int:
    """Archive a pushed context document and return the version now held.

    Last-write-wins by version, and a version at or below the stored one is a no-op rather than
    a refusal: the Runtime may retry a push whose acknowledgement was lost, and there is nothing
    wrong with that.

    The blob is written before the row, never the other way round. A row naming a version whose
    document never arrived would send a cold start off to restore something that is not there,
    whereas a document with no row pointing at it is simply retried and overwritten.

    Both the version check and the blob write happen under the row's lock. Every version of a
    conversation's context shares one blob key, so an unlocked write is exactly what lets a
    slower writer carrying an older document land on top of a newer one -- and then walk the
    row's version back to match it, which is the one outcome a cold start cannot detect.

    :param conversation_id: Conversation the context belongs to.
    :param payload: Context document as ``ConversationContext.as_payload`` produced it.
    :return: The context version now archived.
    :raises ConversationStateError: If the document does not carry a usable version.
    """
    version = payload.get("context_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise ConversationStateError("the context document has no non-negative context_version")

    backend, config = blob_location(conversation_id)
    with transaction.atomic():
        snapshot = _locked_snapshot(conversation_id, backend, config)
        # Re-read under the lock: whoever held it before us may have archived a newer version
        # while this call was waiting, and that one must not be walked back.
        if version <= snapshot.context_version:
            return snapshot.context_version

        snapshot.get_blob_store().put_bytes(json.dumps(payload).encode())
        snapshot.context_version = version
        snapshot.save(update_fields=["context_version", "updated"])
        return version


def context_version(conversation_id: Any) -> int:
    """Return the archived context version, or ``0`` when nothing has been archived yet.

    :param conversation_id: Conversation to look at.
    :return: The version a cold start would resume from.
    """
    snapshot = ConversationContextSnapshot.objects.filter(conversation_id=conversation_id).first()
    return 0 if snapshot is None else snapshot.context_version


def load_context(conversation_id: Any) -> dict[str, Any] | None:
    """Return the archived context document, or ``None`` when there is none.

    :param conversation_id: Conversation to restore.
    :return: The document a cold Runtime can be seeded with.
    :raises ConversationStateError: If the row exists but its document cannot be read back.
    """
    snapshot = ConversationContextSnapshot.objects.filter(conversation_id=conversation_id).first()
    if snapshot is None or snapshot.context_version == 0:
        return None
    try:
        raw = snapshot.get_blob_store().get_bytes()
    except OSError as exc:
        raise ConversationStateError(f"the archived context could not be read: {exc}") from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConversationStateError(f"the archived context is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ConversationStateError(f"the archived context is not a JSON object: {document!r}")
    return document


@transaction.atomic
def clear(conversation_id: Any) -> None:
    """Forget every piece of stored state for one conversation.

    For tests, and for the eventual "start this conversation over" operation. The context blob
    is deliberately left where it is: the row that names it is gone, so nothing can reach it,
    and a failed remote delete must not stop the rows from going away.

    Whoever builds that operation has to revoke the conversation's state tokens as well (see
    :func:`~app_spark_api.agent.conversations.services.revoke_state_access`). Wiping the rows
    while a Runtime still holds a valid token only empties them until its next push.

    :param conversation_id: Conversation to wipe.
    """
    ConversationMessage.objects.filter(conversation_id=conversation_id).delete()
    ConversationUiEvent.objects.filter(conversation_id=conversation_id).delete()
    ConversationContextSnapshot.objects.filter(conversation_id=conversation_id).delete()


# Async wrappers. Every view that touches this runs on the event loop, and Django's async ORM
# has no transactions of its own to hold the row-level guarantees above in -- so the whole
# operation goes to a worker thread rather than being reassembled call by call.
aappend_records = sync_to_async(append_records)
aread_ui_events = sync_to_async(read_ui_events)
asave_context = sync_to_async(save_context)
aload_context = sync_to_async(load_context)
alast_seq = sync_to_async(last_seq)
acontext_version = sync_to_async(context_version)


def _lock_conversation(conversation_id: Any) -> None:
    """Take the conversation's row lock, serializing every writer for that one conversation.

    The conversation row is locked rather than the channel rows, because the rows a batch is
    about to insert do not exist yet -- there is nothing there to lock, and the gap check reads
    an aggregate that no row lock would cover either. The conversation row is the one object
    every writer of this conversation's state has to pass through.

    Only the primary key is selected: the lock is the point, not the row's contents.

    :param conversation_id: Conversation to lock. Must be called inside a transaction.
    :raises ConversationStateError: If the conversation no longer exists.
    """
    locked = Conversation.objects.select_for_update().filter(id=conversation_id).values_list("pk", flat=True).first()
    if locked is None:
        raise ConversationStateError(f"conversation {conversation_id} no longer exists")


def _locked_snapshot(
    conversation_id: Any,
    backend: str,
    config: dict[str, Any],
) -> ConversationContextSnapshot:
    """Return this conversation's context row with its lock held, creating it when missing.

    Created in a separate statement first, because a row that does not exist yet cannot be
    locked. Two writers racing to create it are settled by the primary key, and both then
    contend for the same lock on the survivor.

    Deliberately a different row from the one :func:`_lock_conversation` takes. The context is
    one row that already exists to be locked, so it needs no stand-in -- and keeping the two
    apart means a multi-megabyte blob upload cannot stall the channel appends of a run in
    progress. Neither path takes both locks, so there is no order for them to disagree on.

    :param conversation_id: Conversation whose context row is wanted.
    :param backend: Blob backend to record on a freshly created row.
    :param config: Blob backend configuration to record on a freshly created row.
    :return: The locked row. Must be called inside a transaction.
    """
    ConversationContextSnapshot.objects.get_or_create(
        conversation_id=conversation_id,
        defaults={"backend": backend, "config": config},
    )
    return ConversationContextSnapshot.objects.select_for_update().get(conversation_id=conversation_id)


def _structure_record(
    spec: ChannelSpec,
    conversation_id: Any,
    channel: str,
    raw: dict[str, Any],
) -> ConversationMessage | ConversationUiEvent:
    """Build one unsaved row from a pushed record, or say what is wrong with it."""
    try:
        return spec.model(
            conversation_id=conversation_id,
            seq=raw["seq"],
            run_id=raw["run_id"],
            payload=raw[spec.payload_key],
            recorded_at=_structure_timestamp(raw["timestamp"]),
        )
    except KeyError as exc:
        raise ConversationStateError(f"a {channel} record is missing {exc}") from exc


def _structure_timestamp(raw: object) -> datetime:
    """Parse the Runtime's own ISO-8601 timestamp."""
    if not isinstance(raw, str):
        raise ConversationStateError(f"a record timestamp must be a string, got {raw!r}")
    parsed = parse_datetime(raw)
    if parsed is None:
        raise ConversationStateError(f"a record timestamp is not ISO-8601: {raw!r}")
    return parsed


def _wire_record(row: ConversationMessage | ConversationUiEvent, payload_key: str) -> dict[str, Any]:
    """Return a stored row in the shape the Runtime's own drain endpoint would have used.

    Keeping the shape identical is what lets a client read history from here and live events
    from the stream without knowing which one it got.
    """
    return {
        "seq": row.seq,
        "run_id": row.run_id,
        "timestamp": row.recorded_at.isoformat(),
        payload_key: row.payload,
    }
