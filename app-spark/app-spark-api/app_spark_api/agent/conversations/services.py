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

"""Orchestrating a conversation: the row, its Runtime, and one turn at a time.

Where a conversation's history is read from is the thing to keep straight here. The Runtime is
authoritative only while it is alive, and it is disposable by design -- so this service reads
its own tables, which the Runtime replicates into, and treats a Runtime as something needed
only to *advance* a conversation, never to look at one.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

import attrs
from asgiref.sync import sync_to_async
from django.db.models import F
from django.utils import timezone

from app_spark_api.agent.conversations import checkpoints, state
from app_spark_api.agent.conversations.exceptions import ConversationClosedError
from app_spark_api.agent.conversations.internal_api import state_ingest_path
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.tokens import mint_state_token
from app_spark_api.agent.runtime import (
    AgentRuntimeClient,
    AgentUnavailableError,
    EventPage,
    GitRemote,
    StateCallback,
    get_agent_runtime_provider,
)
from app_spark_api.repository.git.factory import get_repo_server_config
from app_spark_api.repository.git.services import arequire_project_git_ready

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from app_spark_api.agent.runtime import AgentRun, RuntimeHealth
    from app_spark_api.core.projects.models import Project
    from app_spark_api.repository.git.models import ProjectGitRepository

logger = logging.getLogger(__name__)

# Page size for the stored AG-UI event history. Decided here rather than deferred to the
# Runtime's own default, because this read no longer goes anywhere near a Runtime.
DEFAULT_UI_EVENT_PAGE_SIZE = 200
MAX_UI_EVENT_PAGE_SIZE = 1_000

_CLOSED_MESSAGE = "Conversation {id} has been closed and cannot be advanced"


@attrs.frozen
class ConversationState:
    """What this service can say about a conversation without starting anything.

    :param context_version: Version of the archived context a cold start would resume from.
    :param log_seq: Last raw transcript sequence number stored here.
    :param ui_event_seq: Last AG-UI event sequence number stored here.
    :param running: Whether a Runtime is up and currently occupied by a run.
    :param replication_pending: Whether a live Runtime still holds state these cursors do not
        cover yet. ``running`` alone cannot answer "has this turn landed here": the Runtime
        releases its run guard even when the end-of-turn flush timed out, so an idle Runtime
        may still be ahead of this service. ``False`` when no Runtime is up, since there is
        then nothing left that could still arrive.
    :param model: Model of the live Runtime, or ``None`` when none is up. Nothing here can
        answer it otherwise: the model is the agent's own configuration, not this service's.
    """

    context_version: int
    log_seq: int
    ui_event_seq: int
    running: bool
    replication_pending: bool
    model: str | None


async def create_conversation(project: Project, *, owner: str | None) -> Conversation:
    """Create a conversation row, numbered within its Project.

    Runs in a worker thread because allocating the number takes a row lock, and Django's async
    ORM has no transactions of its own to hold one in.

    :param project: Project the conversation belongs to.
    :param owner: pk of the user starting it.
    :return: The stored conversation.
    """
    return await sync_to_async(Conversation.objects.create_for_project)(project, owner=owner)


async def close_conversation(conversation: Conversation) -> None:
    """结束一个会话，并回收它占着的 Agent Runtime。

    结束是终态，也是 Runtime 唯一的对外回收入口：会话一旦结束就不再接受新的一轮对话，于是
    Runtime 连同它占着的 Project workspace 都可以还回去，同一个 Project 的其他会话才能接着用
    （一个 Project 的 workspace 同时只容得下一个 Runtime，见 ``_reject_workspace_conflict``）。

    如果这一刻正好有一轮对话在跑，它会被打断：客户端那条 SSE 流会收到一个 AG-UI ``RUN_ERROR``
    事件（见 :func:`stream_run`）。这是有意的——结束会话本来就是「别跑了」的意思。

    :param conversation: 要结束的会话。就地更新 ``closed_at``，调用方拿它直接构造响应即可，
        不必再回库读一次。
    :raises ConversationClosedError: 会话已经结束过了。
    """
    closed_at = timezone.now()

    # 先落库、再回收 Runtime，而且落库这一步用一条带条件的 UPDATE 而不是「读出来判断一下再写」：
    #
    # * 条件写让并发的两个「结束」里只有一个能改到行，另一个拿到 0 行受影响，于是它知道自己
    #   慢了一步。读-判断-写的话两个都会觉得自己是第一个，各自回一个成功。
    # * 顺序也不能反。这条 UPDATE 才是真正拦住后续对话的东西（见 :func:`start_run` 的闸门），
    #   而停进程是尽力而为的——先停进程再落库，中间失败就会留下一个「Runtime 没了但会话还活着」
    #   的状态，下一轮对话又会把 Runtime 拉起来，等于这次结束什么也没做成。
    #
    # `updated` 一并显式写上：`aupdate()` 绕过 `save()`，`auto_now` 不会被触发。
    changed = (
        await Conversation.objects.get_queryset()
        .filter(pk=conversation.pk)
        .live()
        .aupdate(closed_at=closed_at, updated=closed_at)
    )
    if not changed:
        raise ConversationClosedError(f"Conversation {conversation.id} has already been closed")
    conversation.closed_at = closed_at

    await terminate_runtime(conversation)


async def open_client(conversation: Conversation) -> AgentRuntimeClient:
    """Bring up the conversation's Agent Runtime if needed and return a client for it.

    :param conversation: Conversation to be served.
    :return: A client pointed at a Runtime that has answered ``/health``.
    :raises AgentProvisionError: If no Runtime could be brought up.
    :raises AgentWorkspaceBusyError: If another conversation of the same Project holds one.
    :raises GitRepositoryNotReadyError: If the Project repo is missing or not ready.
    """
    repo = await arequire_project_git_ready(conversation.project_id)
    provider = get_agent_runtime_provider()
    # `project_id` rather than `project`, so this never lazily loads the related row -- an
    # implicit query here would be a synchronous one in an async view.
    handle = await provider.ensure(
        project_id=conversation.project_id,
        conversation_id=str(conversation.id),
        state_callback=_state_callback(conversation),
        git_remote=await sync_to_async(_git_remote)(repo),
    )
    return AgentRuntimeClient(handle)


def _git_remote(repo: ProjectGitRepository) -> GitRemote:
    """Describe the Project's repository for the Runtime that will write to it.

    The clone URL is the one recorded at provisioning time, which is the host as the *sandbox*
    sees it rather than as this process does. The two are the same only while everything runs on
    one machine, and the moment they are not, using this process's own address would point every
    Runtime at itself.

    Wrapped in ``sync_to_async`` by the caller because reading ``write_token`` decrypts it, and
    ``EncryptField`` is not safe to touch from the event loop.
    """
    # `require_project_git_ready` refuses anything without a token, so this cannot be None here.
    assert repo.write_token is not None
    return GitRemote(
        clone_url=repo.clone_url,
        branch=repo.default_branch,
        username=get_repo_server_config().service_account,
        token=repo.write_token,
    )


async def terminate_runtime(conversation: Conversation) -> None:
    """Revoke a conversation's authority to write any more state, and stop its Runtime.

    The two halves belong together, which is why this exists rather than callers reaching for
    the provider. Stopping a process is best-effort -- it may already be gone, it may ignore the
    signal, this service may simply have lost track of it -- whereas revoking the token is not,
    and it is what actually guarantees nothing more arrives under this conversation's name.

    :param conversation: Conversation whose Runtime should be stopped.
    """
    await revoke_state_access(conversation)
    try:
        await get_agent_runtime_provider().terminate(str(conversation.id))
    except Exception:
        logger.exception(
            "The Agent Runtime of conversation %s could not be stopped. It can no longer write "
            "state, but may still be holding this project's workspace.",
            conversation.id,
        )


async def revoke_state_access(conversation: Conversation) -> None:
    """Invalidate every state-ingest token minted for this conversation so far.

    Incrementing in the database rather than from a value read into Python, so two concurrent
    revocations cannot both write the same epoch and leave one of the two token generations
    still valid.

    :param conversation: Conversation to cut off. Refreshed in place, so the caller can mint a
        replacement token from it straight afterwards.
    """
    await Conversation.objects.filter(pk=conversation.pk).aupdate(state_epoch=F("state_epoch") + 1)
    await conversation.arefresh_from_db(fields=["state_epoch"])


async def get_state(conversation: Conversation) -> ConversationState:
    """Report where a conversation stands, without starting a Runtime for it.

    Not starting one is the point. Opening a conversation to look at it used to provision an
    agent, which is expensive for a question that the stored state can answer on its own.

    :param conversation: Conversation to describe.
    :return: The cursors this service holds, plus whatever a live Runtime adds.
    """
    context_version, log_seq, ui_event_seq = await sync_to_async(_stored_cursors)(conversation.id)

    provider = get_agent_runtime_provider()
    handle = await provider.peek(str(conversation.id))
    model: str | None = None
    running = False
    replication_pending = False
    if handle is not None:
        health = await AgentRuntimeClient(handle).health()
        model = health.model
        running = health.running
        replication_pending = health.replication_pending

    return ConversationState(
        context_version=context_version,
        log_seq=log_seq,
        ui_event_seq=ui_event_seq,
        running=running,
        replication_pending=replication_pending,
        model=model,
    )


async def read_ui_events(
    conversation: Conversation,
    *,
    since: int = 0,
    limit: int | None = None,
) -> EventPage:
    """Read one page of the conversation's AG-UI event history from this service's own tables.

    Deliberately not from the Runtime. This is the read behind "open a conversation and see
    what happened in it", and a conversation whose Runtime is long gone has to answer it just
    as well as one still in progress.

    :param conversation: Conversation to read.
    :param since: Cursor to resume from; ``0`` starts at the beginning.
    :param limit: Page size, capped at :data:`MAX_UI_EVENT_PAGE_SIZE`.
    :return: One page, plus the cursor needed to ask for the next.
    """
    page_size = min(limit or DEFAULT_UI_EVENT_PAGE_SIZE, MAX_UI_EVENT_PAGE_SIZE)
    records, last_seq = await state.aread_ui_events(conversation.id, since=since, limit=page_size)
    return EventPage(since=since, last_seq=last_seq, records=records)


async def start_run(conversation: Conversation, *, content: str) -> AgentRun:
    """Submit one turn and return its open event stream.

    The context version is read from ``/health`` immediately before the run rather than
    remembered between turns. Compaction can move it in the middle of a run, so a version
    carried over from the previous turn is not merely stale, it is wrong often enough to matter.

    :param conversation: Conversation the turn belongs to.
    :param content: The user's message.
    :return: The accepted run, whose bytes are still to come.
    :raises ConversationClosedError: If the conversation has been closed.
    :raises AgentBusyError: If a run is already occupying the Runtime.
    :raises AgentProvisionError: If no Runtime could be brought up.
    :raises AgentUnavailableError: If the Runtime cannot be reached or refuses the turn.
    """
    # 这道闸门是「结束会话」有意义的前提。没有它，结束一个会话只是杀掉了一个进程：下一轮对话
    # 会照常把 Runtime 重新拉起来，被回收的 workspace 也会被重新占上。
    if not conversation.is_live:
        raise ConversationClosedError(_CLOSED_MESSAGE.format(id=conversation.id))

    client = await open_client(conversation)
    await _reject_if_closed_meanwhile(conversation)
    health = await client.health()
    health = await _resume_if_cold(conversation, client, health)
    return await client.start_run(content=content, context_version=health.context_version)


async def _reject_if_closed_meanwhile(conversation: Conversation) -> None:
    """Runtime 拉起来之后，回库再确认一次这个会话还活着。

    :func:`start_run` 开头那道闸门看的是请求进来时读到的那一行，而 :func:`open_client` 要花上
    好几秒才回来。这中间足够另一个请求把会话结束掉，于是这一轮会为一个已经结束的会话拉起
    Runtime：刚交还的 Project workspace 又被占上（同一个 Project 的下一个会话于是开不起来），
    而它手里那张回写 token 已经被 close 吊销了——这一轮跑得成功，却什么都写不回来。

    检查放在 ``open_client()`` **之后**才兜得住，因为两边的顺序正好相反：close 是先落库、
    再收 Runtime，这里是先拉起 Runtime（provider 里已经登记）、再回库读。于是不管这两个请求
    怎么交错，总有一边能看见对方：

    * close 的 UPDATE 落在这次读之前——这里读到「已结束」，Runtime 由这里收掉；
    * close 的 UPDATE 落在这次读之后——那它的 terminate 必然晚于上面的 ``ensure()``，能在
      provider 里找到这个 Runtime，由 close 收掉。

    :param conversation: 要确认的会话。
    :raises ConversationClosedError: 会话在这期间被结束了。抛出之前会先把 Runtime 收掉。
    """
    if await Conversation.objects.get_queryset().filter(pk=conversation.pk).live().aexists():
        return

    logger.warning(
        "Conversation %s was closed while its Agent Runtime was coming up, taking the Runtime back down",
        conversation.id,
    )
    await terminate_runtime(conversation)
    raise ConversationClosedError(_CLOSED_MESSAGE.format(id=conversation.id))


async def _resume_if_cold(
    conversation: Conversation,
    client: AgentRuntimeClient,
    health: RuntimeHealth,
) -> RuntimeHealth:
    """Hand an untouched Runtime the conversation it is supposed to be continuing.

    This is where a cold start actually happens, and it is on the run path rather than at
    provisioning time because that is the first moment the history is genuinely needed.

    A Runtime is only treated as untouched when it reports both no conversation and version 0.
    Either alone would be ambiguous, and injecting into a Runtime that already holds a
    conversation would be destroying one.

    Files come back before the conversation does. In between the two, the Runtime is a process
    that remembers writing code which is not on disk yet, and a run arriving in that window
    would have the model act on the mismatch. Nothing accepts runs until both are done, which
    is what the caller's ordering gives us for free.

    :return: The health to start the run against, unchanged when there was nothing to resume.
    :raises AgentUnavailableError: If a checkpoint exists but its files could not be restored.
    """
    if health.conversation_id is not None or health.context_version != 0:
        return health

    document = await _restore_files(conversation, client)
    if document is None:
        document = await state.aload_context(conversation.id)
    if document is None:
        return health

    # Read now, not taken from the checkpoint. The checkpoint's own cursors were recorded when
    # its commit reached the remote, which is before that turn's events have finished being
    # replicated here -- and seeding a Runtime below the real cursor makes it number its first
    # entry over one that already exists, where the ingest's own idempotency silently drops it.
    # The channels are append-only and nothing truncates them, so "where we are now" is always
    # the right place for the next entry to go.
    log_seq = await state.alast_seq(conversation.id, state.MESSAGE_CHANNEL)
    ui_event_seq = await state.alast_seq(conversation.id, state.UI_EVENT_CHANNEL)
    restored_version = await client.restore_context(
        document,
        if_match=health.context_version,
        log_seq=log_seq,
        ui_event_seq=ui_event_seq,
    )
    logger.info(
        "Conversation %s was resumed on a cold Runtime at context version %d, "
        "continuing from log seq %d and ui event seq %d",
        conversation.id,
        restored_version,
        log_seq,
        ui_event_seq,
    )
    return attrs.evolve(health, context_version=restored_version)


async def _restore_files(conversation: Conversation, client: AgentRuntimeClient) -> dict[str, Any] | None:
    """Put the workspace back to this conversation's checkpoint, and return its paired context.

    ``None`` means there was no checkpoint to restore from and the files were left alone, which
    covers both "this Project has no repository" and "the last turn only got half-way saved".
    Neither is an error: a half-saved turn is not a restore point, and continuing from a slightly
    older place beats continuing with files and memory that disagree.

    :raises AgentUnavailableError: If a checkpoint exists but cannot be honoured.
    """
    checkpoint = await checkpoints.alatest_restorable(conversation.id)
    if checkpoint is None:
        return None

    # A checkpoint the conversation has already moved past is not usable, even though both its
    # halves are here. Seeding the Runtime with an older version would have it re-issue version
    # numbers this service has already archived, and `save_context` refuses to go backwards --
    # so every turn from then on would be silently dropped. This happens only when a later turn
    # took the "continue without saving" escape hatch, and in that case the branch tip is this
    # checkpoint's commit anyway, so leaving the files alone lands in the same place.
    newest = await state.acontext_version(conversation.id)
    if checkpoint.context_version != newest:
        logger.warning(
            "Conversation %s has a checkpoint at context version %d but has since archived "
            "version %d, so its files are being left as they are",
            conversation.id,
            checkpoint.context_version,
            newest,
        )
        return None

    outcome = await client.restore_workspace(checkpoint.commit)
    document = await state.aload_context_version(conversation.id, checkpoint.context_version)
    if document is None:
        # The checkpoint was found *because* its version row exists, so failing to read the
        # document means the row and the blob disagree. Carrying on would pair files we have
        # just restored with a context from somewhere else, so this fails out loud.
        raise AgentUnavailableError(
            f"The checkpoint at {checkpoint.commit} names context version "
            f"{checkpoint.context_version}, which is no longer readable."
        )
    logger.info(
        "Conversation %s restored its workspace to checkpoint %s (%s)",
        conversation.id,
        checkpoint.commit,
        outcome,
    )
    return document


def _state_callback(conversation: Conversation) -> StateCallback:
    """Describe where a Runtime for this conversation should replicate its state.

    The path only; the provider adds the host, because only it knows where this service is
    reachable from wherever the Runtime is about to run.

    The token is minted against the conversation's current epoch, so a Runtime spawned after a
    revocation is authorized while its predecessor stays cut off.
    """
    return StateCallback(
        path=state_ingest_path(conversation.id),
        token=mint_state_token(conversation.id, epoch=conversation.state_epoch),
    )


def _stored_cursors(conversation_id: UUID) -> tuple[int, int, int]:
    """Return the archived context version and both channel cursors, in one thread hop."""
    document_version = state.context_version(conversation_id)
    return (
        document_version,
        state.last_seq(conversation_id, state.MESSAGE_CHANNEL),
        state.last_seq(conversation_id, state.UI_EVENT_CHANNEL),
    )


async def stream_run(run: AgentRun, conversation_id: UUID) -> AsyncIterator[bytes]:
    """Forward a run's AG-UI events, turning a mid-stream failure into a final event.

    Once the first byte is out the status code is spent, so a connection that breaks here cannot
    be reported as an HTTP error. AG-UI has its own way to say a run ended badly, and a client
    that receives it can show something better than a stream that simply stopped.
    """
    try:
        async for chunk in run.aiter_bytes():
            yield chunk
    except Exception as exc:
        logger.exception("The event stream of conversation %s broke mid-run", conversation_id)
        yield _sse_frame(
            {
                "type": "RUN_ERROR",
                "timestamp": int(time.time() * 1000),
                "runId": run.run_id,
                "message": f"The Agent Runtime stopped responding: {exc}",
            }
        )


def _sse_frame(event: dict[str, Any]) -> bytes:
    """Encode one event the way the Agent Runtime encodes its own."""
    return f"data: {json.dumps(event)}\n\n".encode()
