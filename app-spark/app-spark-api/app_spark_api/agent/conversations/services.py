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

"""Orchestrating a conversation: the row and its Runtime.

Starting something on that Runtime -- a turn, or the preview -- is in
:mod:`app_spark_api.agent.conversations.lifecycle`.

Where a conversation's history is read from is the thing to keep straight here. The Runtime is
authoritative only while it is alive, and it is disposable by design -- so this service reads
its own tables, which the Runtime replicates into, and treats a Runtime as something needed
only to *advance* a conversation, never to look at one.
"""

from __future__ import annotations

import json
import logging
import time
from functools import partial
from typing import TYPE_CHECKING, Any

import attrs
from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from app_spark_api.agent.conversations import state
from app_spark_api.agent.conversations.exceptions import (
    ConversationClosedError,
    RunNotFoundError,
    RunNotInProgressError,
)
from app_spark_api.agent.conversations.internal_api import state_ingest_path
from app_spark_api.agent.conversations.models import Conversation, ConversationUserMessage
from app_spark_api.agent.conversations.state_models import ConversationContextVersion
from app_spark_api.agent.conversations.tokens import mint_state_token
from app_spark_api.agent.model_catalog.services import resolve_model_access
from app_spark_api.agent.runtime import (
    AgentProvisionError,
    AgentRuntimeClient,
    AgentUnavailableError,
    EventPage,
    GitRemote,
    StateCallback,
)
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from app_spark_api.agent.runtime.lifetime import extend_lifetime_quietly
from app_spark_api.repository.git.factory import get_repo_server_config
from app_spark_api.repository.git.services import arequire_project_git_ready

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from app_spark_api.agent.runtime import AgentRun, PreviewTarget
    from app_spark_api.core.projects.models import Project
    from app_spark_api.infras.bk_access_token import UserCredential
    from app_spark_api.repository.git.models import ProjectGitRepository

logger = logging.getLogger(__name__)

# Page size for the stored AG-UI event history. Decided here rather than deferred to the
# Runtime's own default, because this read no longer goes anywhere near a Runtime.
DEFAULT_UI_EVENT_PAGE_SIZE = 200
MAX_UI_EVENT_PAGE_SIZE = 1_000


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
    :param dev_server_status: What the live Runtime says about the workspace application it
        supervises. ``None`` when no Runtime is up, because whether that application is
        listening is a fact about a running sandbox and nothing stored here can stand in for it.
    :param runtime_ready: Whether the next turn can go straight to the Runtime that is up now.
        False when none is up, the one that is up does not answer, or the provider is going
        to replace it anyway; the next turn then has to prepare one first, which takes a while.
    :param run_id: The turn the live Runtime is running, which is what :func:`stop_run` takes.
        ``None`` when nothing is running, and also briefly at the start of a turn that is
        ``running`` but not under way yet.
    """

    context_version: int
    log_seq: int
    ui_event_seq: int
    running: bool
    replication_pending: bool
    model: str | None
    dev_server_status: str | None = None
    runtime_ready: bool = False
    run_id: str | None = None


async def get_dev_server_status(conversation: Conversation) -> str | None:
    """Ask the live Runtime how the conversation's application is doing, without starting one.

    Deliberately never fails. A Runtime that cannot be reached, or whose sandbox cannot be
    inspected, is reported as nothing to show right now. The preview address is a separate
    query and, for a remote sandbox, changes when that sandbox is replaced.

    :param conversation: Conversation whose application is being looked at.
    :return: The Runtime's own word for the application's state, or ``None`` when nothing could
        be asked. A client only has to branch on whether there is a status at all: no second,
        derived field says the same thing in other words.
    """
    # peek 问不了控制面时抛的是 AgentProvisionError，不是连不上 Runtime 时的 AgentUnavailableError。
    # 不接住的话预览轮询会 502，和上面「这个查询不会失败」相反。
    try:
        handle = await get_agent_runtime_provider().peek(str(conversation.id))
    except AgentProvisionError:
        logger.info(
            "Conversation %s has a Runtime that cannot be inspected, reporting its application as unknown",
            conversation.id,
        )
        return None

    # 没有 Runtime 是常态而不是故障：会话可能刚建、也可能被回收过。
    if handle is None:
        return None

    try:
        health = await AgentRuntimeClient(handle).health()
    except AgentUnavailableError:
        # 降成 info 且不带 traceback：Runtime 死掉但还没被回收的那段时间里，前端每轮询一次就会
        # 走到这里，按 warning 打会把日志刷满。真正需要人看的是 Runtime 为什么死，不在这条上。
        logger.info(
            "Conversation %s has a Runtime that cannot be read, reporting its application as unknown",
            conversation.id,
        )
        return None

    return health.dev_server_status


async def get_preview_target(conversation: Conversation) -> PreviewTarget | None:
    """Return where the conversation's preview is served, and how a caller reaches it.

    :param conversation: Conversation whose application is to be previewed.
    :return: The application's address with its transport, or ``None`` when no Runtime is
        serving the conversation. A public target is opened by the browser; any other target
        is proxied by this service.
    """
    return await get_agent_runtime_provider().preview_target(str(conversation.id))


async def create_conversation(project: Project, *, owner: str | None) -> Conversation:
    """Create a conversation row, numbered within its Project.

    Runs in a worker thread because allocating the number takes a row lock, and Django's async
    ORM has no transactions of its own to hold one in.

    :param project: Project the conversation belongs to.
    :param owner: pk of the user starting it.
    :return: The stored conversation.
    """
    return await sync_to_async(Conversation.objects.create_for_project)(project, owner=owner)


async def aclose_project_conversations(project_id: str) -> None:
    """End every live conversation of a Project and revoke their state-ingest tokens."""
    closed_at = timezone.now()

    # 推进 state_epoch：Runtime 停止前的最后一次状态回写会被拒绝。
    await (
        Conversation.objects.get_queryset()
        .filter(project_id=project_id)
        .live()
        .aupdate(closed_at=closed_at, updated_at=closed_at, state_epoch=F("state_epoch") + 1)
    )


def delete_project_conversations(project_id: str) -> None:
    """Delete every conversation and context document belonging to a Project."""
    with transaction.atomic():
        # 级联删除会带走记着 blob 位置的版本行，所以要先读出来。
        versions = list(
            ConversationContextVersion.objects.filter(
                conversation__project_id=project_id,
            ).select_related("conversation")
        )
        stores = [version.get_blob_store() for version in versions]

        Conversation.objects.filter(project_id=project_id).delete()
        for version, store in zip(versions, stores, strict=True):
            logger.debug(
                "Deleting context version %s of conversation %s for project %s",
                version.context_version,
                version.conversation_id,
                project_id,
            )
            store.delete()


async def adelete_project_conversations(project_id: str) -> None:
    """Async wrapper for :func:`delete_project_conversations`."""
    await sync_to_async(delete_project_conversations)(project_id)


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
    # * 顺序也不能反。这条 UPDATE 才是真正拦住后续对话的东西（见 ``lifecycle.start.start_run`` 的闸门），
    #   而停进程是尽力而为的——先停进程再落库，中间失败就会留下一个「Runtime 没了但会话还活着」
    #   的状态，下一轮对话又会把 Runtime 拉起来，等于这次结束什么也没做成。
    #
    # `updated_at` 一并显式写上：`aupdate()` 绕过 `save()`，`auto_now` 不会被触发。
    changed = (
        await Conversation.objects.get_queryset()
        .filter(pk=conversation.pk)
        .live()
        .aupdate(closed_at=closed_at, updated_at=closed_at)
    )
    if not changed:
        raise ConversationClosedError(f"Conversation {conversation.id} has already been closed")
    conversation.closed_at = closed_at

    await terminate_runtime(conversation)


async def open_client(conversation: Conversation, *, credential: UserCredential | None = None) -> AgentRuntimeClient:
    """Bring up the conversation's Agent Runtime if needed and return a client for it.

    :param conversation: Conversation to be served.
    :param credential: The caller's BlueKing login. Needed only when a Runtime has to be started
        and its model calls go through bkaidev, to get the caller's access_token.
    :return: A client pointed at a Runtime that has answered ``/health``.
    :raises AgentProvisionError: If no Runtime could be brought up.
    :raises AgentWorkspaceBusyError: If another conversation of the same Project holds one.
    :raises GitRepositoryNotReadyError: If the Project repo is missing or not ready.
    :raises ModelAccessConfigurationError: If a Runtime must be started and the model source or
        its settings are invalid, or no model is left to run on.
    :raises ModelCredentialMissingError: If a Runtime must be started for bkaidev and
        ``credential`` is None.
    :raises AccessTokenUnavailableError: If a Runtime must be started and the caller's
        access_token could not be obtained.
    :raises BkAidevGatewayError: If a Runtime must be started for bkaidev and the gateway could
        not give the model list its default model comes from.
    """
    repo = await arequire_project_git_ready(conversation.project_id)

    # 交给 provider 的是解析函数而不是结果：只有它知道这次是否真要新起 Runtime。每轮对话都走到
    # 这里，已在跑的 Runtime 手里早有 token，提前解析就是每条消息一次换票。
    # `project_id` rather than `project`, so this never lazily loads the related row -- an
    # implicit query here would be a synchronous one in an async view.
    handle = await get_agent_runtime_provider().ensure(
        project_id=conversation.project_id,
        conversation_id=str(conversation.id),
        state_callback=_state_callback(conversation),
        git_remote=await sync_to_async(_git_remote)(repo),
        model_access=partial(resolve_model_access, credential),
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

    # 同步等 provider 停完：e2b 会先让 Agent 推送工作区，最多等 STOP_GRACE_SECONDS 再销毁沙箱。凭证已吊销，
    # Agent 退出前最后那次状态回写会被拒绝，会话历史以此前已回写的为准。
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

    stored = ConversationState(
        context_version=context_version,
        log_seq=log_seq,
        ui_event_seq=ui_event_seq,
        running=False,
        replication_pending=False,
        model=None,
    )

    provider = get_agent_runtime_provider()
    handle = await provider.peek(str(conversation.id))
    if handle is None:
        return stored

    try:
        health = await AgentRuntimeClient(handle).health()
    except AgentUnavailableError:
        # Agent 空闲退出或崩溃、而沙箱还没被回收的那段时间里，前端每轮询一次都会走到这里。
        # 如实报「没有可用的运行环境」，不重建也不回收：那是下一轮对话 ensure 的事，查询不写数据。
        # 同 get_dev_server_status，按 info 打、不带 traceback，免得轮询把日志刷满。
        logger.info("Conversation %s has a Runtime that cannot be read, reporting none", conversation.id)
        return stored

    return attrs.evolve(
        stored,
        running=health.running,
        replication_pending=health.replication_pending,
        model=health.model,
        dev_server_status=health.dev_server_status,
        run_id=health.run_id,
        # 有一轮在跑时 ensure 不会换掉它（超龄也一样），下一轮要么复用、要么因忙被拒，都不用准备。
        runtime_ready=health.running or not await provider.needs_replacement(str(conversation.id)),
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


async def stop_run(conversation: Conversation, run_id: str) -> None:
    """请求停下这个会话正在跑的那一轮，不等它真正收尾就返回。

    一轮对话不随客户端连接结束：浏览器刷新、网络断开都不会打断它（见 :func:`stream_run`）。
    想让它提前结束，只能显式调用这里。Runtime 会按「停止」收尾：这一轮已经做了的部分照样提交为
    会话上下文，文件以「被中断」提交，事件流以 ``RUN_FINISHED`` 结束。收尾完成的标志是
    :func:`get_state` 的 ``running`` 变回 false。

    只看、不拉：没有 Runtime 就没有在跑的一轮，不能为了停一轮去拉起一个 Runtime。

    :param conversation: 这一轮所属的会话。
    :param run_id: 要停的那一轮。点名是为了不误停：请求晚到时，Runtime 上跑的可能已经是下一轮。
    :raises RunNotFoundError: 这个会话从来没有接受过这一轮。
    :raises RunNotInProgressError: 这一轮已经结束，或者它所在的 Runtime 已经不在了。
    :raises AgentUnavailableError: Runtime 联系不上，或者回了不该回的东西。
    """
    # 先认归属，再问 Runtime：run_id 是客户端传来的，不能让它借这个会话的 Runtime 去试探别的会话。
    if not await ConversationUserMessage.objects.filter(conversation=conversation, run_id=run_id).aexists():
        raise RunNotFoundError(f"Conversation {conversation.id} has no run {run_id}")

    handle = await get_agent_runtime_provider().peek(str(conversation.id))
    if handle is None or not await AgentRuntimeClient(handle).stop_run(run_id):
        raise RunNotInProgressError(f"Run {run_id} of conversation {conversation.id} is not in progress")
    logger.info("Conversation %s asked its Agent Runtime to stop run %s", conversation.id, run_id)


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

    Forwarding is all this does. A client that goes away cancels it, which closes the connection
    to the Runtime -- and that only stops the Runtime sending: the turn itself runs on there and
    replicates what it produced as usual. Ending a turn early is :func:`stop_run`.
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
    finally:
        # 一轮开始时 ensure 已经把存活期续成空闲超时。这里再续一次，从流结束起再算同一个秒数。
        # 流断了、客户端走了也照样续；但那时这一轮可能还在跑，它真正结束时由状态回写那边再续一次，
        # 见 internal_api.append_ui_events。进行中不再续，一轮按不超过空闲超时来对待。
        await extend_lifetime_quietly(get_agent_runtime_provider(), conversation_id)


def _sse_frame(event: dict[str, Any]) -> bytes:
    """Encode one event the way the Agent Runtime encodes its own."""
    return f"data: {json.dumps(event)}\n\n".encode()
