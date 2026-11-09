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

"""What starting a turn and starting the preview share: the closed-meanwhile check and the cold resume."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

import attrs

from app_spark_api.agent.conversations import checkpoints, state
from app_spark_api.agent.conversations.exceptions import ConversationClosedError
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.services import terminate_runtime
from app_spark_api.agent.runtime import AgentBusyError, AgentUnavailableError
from app_spark_api.agent.runtime.client import CONTEXT_TIMEOUT_SECONDS

if TYPE_CHECKING:
    from app_spark_api.agent.runtime import AgentRuntimeClient, RuntimeHealth

logger = logging.getLogger(__name__)

CLOSED_MESSAGE = "Conversation {id} has been closed and cannot be advanced"

# How long a request turned down by a concurrent resume waits for it to finish. A resume is the
# files and then the context, each bounded on the Runtime client by CONTEXT_TIMEOUT_SECONDS.
CONCURRENT_RESUME_WAIT_SECONDS = 2 * CONTEXT_TIMEOUT_SECONDS
CONCURRENT_RESUME_POLL_SECONDS = 0.5


async def reject_if_closed_meanwhile(conversation: Conversation) -> None:
    """Runtime 拉起来之后，回库再确认一次这个会话还活着。

    :func:`~app_spark_api.agent.conversations.lifecycle.start.start_run` 开头那道闸门看的是请求进来时读到的那一行，而 :func:`~app_spark_api.agent.conversations.services.open_client` 要花上
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
    raise ConversationClosedError(CLOSED_MESSAGE.format(id=conversation.id))


async def resume_if_cold(
    conversation: Conversation,
    client: AgentRuntimeClient,
    health: RuntimeHealth,
) -> RuntimeHealth:
    """Hand an untouched Runtime the conversation it is supposed to be continuing.

    This is where a cold start actually happens, and it is on the run path rather than at
    provisioning time because that is the first moment the history is genuinely needed.

    A Runtime is only treated as untouched when it reports no conversation, version 0 and no
    entries in either channel. Any one alone would be ambiguous, and injecting into a Runtime
    that already holds a conversation would be destroying one. The channels count because a
    first turn can fail before committing any context: that Runtime still reads as version 0,
    but it has numbered entries of its own and can no longer be told where to start.

    Files come back before the conversation does. In between the two, the Runtime is a process
    that remembers writing code which is not on disk yet, and a run arriving in that window
    would have the model act on the mismatch. Nothing accepts runs until both are done, which
    is what the caller's ordering gives us for free.

    The two halves are not required to describe the same moment. The files belong to the
    Project: they come from the conversation's latest checkpoint, or from a newer remote branch
    tip when another conversation has developed the Project since. The conversation is always
    the newest archived one. Turns that change no files leave no checkpoint behind, so the
    conversation being ahead of the files is the ordinary case; the files can be ahead too, when
    a turn's commit was reported but its final context never arrived. Either way the Agent is
    left to notice the difference itself.

    Two requests can find the same Runtime cold -- entering a Project starts the preview, and the
    user's first message is close behind. The Runtime takes the restores one at a time and turns
    the late one down rather than queueing it, and that is not a failure here: whoever got there
    first is doing exactly this. Being turned down only says the other restore has started, not
    that it has finished -- it may still be putting the files back, seconds away from the context
    -- so the late request waits for the Runtime to stop reading as cold, see
    :func:`_wait_for_concurrent_resume`.

    :return: The health to start the run against, unchanged when there was nothing to resume.
    :raises AgentBusyError: If the Runtime stayed occupied and cold for longer than a resume takes.
    :raises AgentUnavailableError: If a checkpoint exists but its files could not be restored.
    """
    if not _is_cold(health):
        return health

    try:
        return await _resume(conversation, client, health)
    except AgentBusyError as exc:
        return await _wait_for_concurrent_resume(conversation, client, exc)
    except AgentUnavailableError as exc:
        return await _resumed_by_someone_else(conversation, client, exc)


async def _wait_for_concurrent_resume(
    conversation: Conversation,
    client: AgentRuntimeClient,
    refusal: AgentBusyError,
) -> RuntimeHealth:
    """Wait out the request that is resuming the Runtime, after it turned this one's restore down.

    Waiting is bounded by :data:`CONCURRENT_RESUME_WAIT_SECONDS`. A Runtime that falls idle while
    still cold had its restore given up -- the other request failed, or let go between the files
    and the context -- and is resumed here once, so a real failure is reported as itself rather
    than as the refusal that started the wait. A Runtime that cannot be reached any more, as
    after the conversation is closed and its Runtime taken down, ends the wait with that error.

    :param refusal: What the Runtime answered this request's own restore with, raised when the
        wait runs out.
    :raises AgentBusyError: If the Runtime is still occupied and cold when the wait runs out, or
        turns the retried resume down too, as one without a Git workspace does.
    :raises AgentUnavailableError: If the Runtime cannot be reached, or the retried resume fails.
    """
    deadline = time.monotonic() + CONCURRENT_RESUME_WAIT_SECONDS
    retried = False
    while True:
        current = await client.health()
        if not _is_cold(current):
            _log_resumed_concurrently(conversation, current)
            return current

        if not current.running and not retried:
            retried = True
            logger.info(
                "Conversation %s found its Runtime cold and idle after a refused restore, resuming it again",
                conversation.id,
            )
            try:
                return await _resume(conversation, client, current)
            except AgentBusyError as exc:
                # Someone took the Runtime again in between, which is the wait this already is.
                refusal = exc
            except AgentUnavailableError as exc:
                return await _resumed_by_someone_else(conversation, client, exc)
        elif not current.running or time.monotonic() >= deadline:
            raise refusal

        await asyncio.sleep(CONCURRENT_RESUME_POLL_SECONDS)


async def _resumed_by_someone_else(
    conversation: Conversation,
    client: AgentRuntimeClient,
    failure: AgentUnavailableError,
) -> RuntimeHealth:
    """Return the Runtime as another request resumed it, or raise the failure of this one's restore.

    A restore the Runtime took but could not do. The one such answer that is not a real failure is
    a context whose If-Match another request has just moved past, and that request has finished
    by then, so a single read tells the two apart.

    :raises AgentUnavailableError: ``failure``, if the Runtime is still cold.
    """
    current = await client.health()
    if _is_cold(current):
        raise failure
    _log_resumed_concurrently(conversation, current)
    return current


def _log_resumed_concurrently(conversation: Conversation, health: RuntimeHealth) -> None:
    logger.info(
        "Conversation %s was resumed by a concurrent request, continuing at context version %d",
        conversation.id,
        health.context_version,
    )


def _is_cold(health: RuntimeHealth) -> bool:
    """Return whether a Runtime is untouched, see :func:`resume_if_cold`."""
    return (
        health.conversation_id is None
        and health.context_version == 0
        and health.log_seq == 0
        and health.ui_event_seq == 0
    )


async def _resume(
    conversation: Conversation,
    client: AgentRuntimeClient,
    health: RuntimeHealth,
) -> RuntimeHealth:
    """Restore the files, then the context or at least the numbering, into a cold Runtime."""
    document = await _restore_files(conversation, client)

    # Read now, not taken from the checkpoint. The checkpoint's own cursors were recorded when
    # its commit reached the remote, which is before that turn's events have finished being
    # replicated here -- and seeding a Runtime below the real cursor makes it number its first
    # entry over one that already exists, where the ingest's own idempotency silently drops it.
    # The channels are append-only and nothing truncates them, so "where we are now" is always
    # the right place for the next entry to go.
    log_seq = await state.alast_seq(conversation.id, state.MESSAGE_CHANNEL)
    ui_event_seq = await state.alast_seq(conversation.id, state.UI_EVENT_CHANNEL)
    if document is None:
        return await _resume_numbering_only(conversation, client, health, log_seq=log_seq, ui_event_seq=ui_event_seq)

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


async def _resume_numbering_only(
    conversation: Conversation,
    client: AgentRuntimeClient,
    health: RuntimeHealth,
    *,
    log_seq: int,
    ui_event_seq: int,
) -> RuntimeHealth:
    """Continue a conversation that has entries stored here but no archived context.

    The Runtime pushes its channels before its context, so one lost during the conversation's
    first turn leaves exactly this behind. There is no memory to hand back, but the numbering
    still has to continue past what is stored: the ingest treats a repeated seq as a redelivery
    and drops it, so a Runtime restarting at 1 would lose its first entries without an error.
    """
    if log_seq == 0 and ui_event_seq == 0:
        return health

    await client.restore_cursors(log_seq=log_seq, ui_event_seq=ui_event_seq)
    logger.warning(
        "Conversation %s was resumed on a cold Runtime without any archived context, "
        "continuing from log seq %d and ui event seq %d",
        conversation.id,
        log_seq,
        ui_event_seq,
    )
    return attrs.evolve(health, log_seq=log_seq, ui_event_seq=ui_event_seq)


async def _restore_files(conversation: Conversation, client: AgentRuntimeClient) -> dict[str, Any] | None:
    """Put the workspace back to this conversation's checkpoint, and return the latest context.

    When the conversation has never pushed a checkpoint, the files are left alone and the newest
    archived context is returned.

    :raises AgentUnavailableError: If the Runtime cannot restore the checkpoint's commit.
    :raises AgentBusyError: If a run is occupying the Runtime, or it has no Git workspace.
    :raises ConversationStateError: If the newest archived context cannot be read back.
    """
    checkpoint = await checkpoints.alatest(conversation.id)
    if checkpoint is None:
        return await state.aload_context(conversation.id)

    # 决策说明：冷启动不要求 checkpoint.context_version 与最新 context_version 严格相等。
    # 会话上下文（对话/压缩）与工作区代码（Git 提交）正交：纯对话轮次、上下文压缩或上报失败后重启
    # 都会使 context 领先于 checkpoint。旧沙箱既已销毁，因版本不等抛 502 只会让项目永久死锁；
    # 直接恢复最新代码快照与最新上下文，若有差异交由 Agent 自行感知处理。
    outcome = await client.restore_workspace(checkpoint.commit)
    document = await state.aload_context(conversation.id)
    # Info rather than a warning when the versions differ: every chat-only turn opens that gap,
    # and from here it looks the same as a lost push. Logging both is what lets a "the Agent
    # said it wrote that file" report be traced to the moment each half came from.
    logger.info(
        "Conversation %s restored its workspace to checkpoint %s at context version %d (%s), "
        "resuming with context version %s",
        conversation.id,
        checkpoint.commit,
        checkpoint.context_version,
        outcome,
        None if document is None else document.get("context_version"),
    )
    return document
