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

"""检查点：一个会话推到 Project 仓库里的提交，冷启动时据此把工作区文件放回去。

Runtime 把 commit 和钉住它的 tag 都推到远端之后才上报，所以一行检查点存在，就说明那份代码在
远端可达，可以直接用来恢复。

检查点和会话上下文是脱钩的。工作区属于 Project，会被多个会话接着开发，远端分支又只能快进，
所以冷启动时工作区最终落在远端分支的最新提交上，检查点只用来确认「这个会话推过的代码还在那段
历史里」（见 Runtime 的 ``restore_to``）；上下文属于会话，冷启动总是注入最新归档的那一版（见
``services._restore_files``）。没改文件的轮次不产生检查点，所以两者版本号不一致是常态，不是
异常。``context_version`` 只作为「这次提交是在哪一版上下文时做的」的记录保留下来，供排查用。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import attrs
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction

from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.state_models import (
    ConversationCheckpoint,
    ConversationContextVersion,
)

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


@attrs.frozen
class Reclaimed:
    """一次回收各拿走了多少东西。

    :param checkpoints: 删掉的检查点数。
    :param versions: 删掉的上下文版本数。
    """

    checkpoints: int = 0
    versions: int = 0


def versions_kept() -> int:
    """一个会话保留多少个最近的上下文版本。"""
    # 至少保留 1 个作为冷启动所使用的上下文
    return max(1, int(settings.AGENT_CONTEXT_VERSIONS_KEPT))


def checkpoints_kept() -> int:
    """一个会话保留多少个最近的检查点。

    同样抬到至少 1：一个检查点都不留，等于关掉工作区恢复。
    """
    return max(1, int(settings.AGENT_CHECKPOINTS_KEPT))


def record(
    conversation_id: UUID,
    *,
    run_id: str,
    commit: str,
    tag: str,
    context_version: int,
    completed: bool,
    log_seq: int,
    ui_event_seq: int,
    state_epoch: int,
) -> None:
    """记下一个 Runtime 报上来的检查点。登记完它就是这个会话冷启动时的恢复目标。

    幂等：同一个 commit 重复上报会更新原行而不是新建一行。Runtime 在确认回执丢失时**必须**重报
    同一个检查点，而不是再做一次提交——代码已经在远端了，再提交只会多出一个内容相同的 SHA。

    :param conversation_id: 检查点所属会话。
    :param run_id: 产生这次提交的 run。
    :param commit: 已在远端的提交 SHA。
    :param tag: 钉住该提交的不可移动远端 tag。
    :param context_version: 做这次提交时会话所在的上下文版本，只作记录。
    :param completed: 该 run 是否完整结束，只作记录；中断的那一轮提交同样已经在远端分支上。
    :param log_seq: 原始记录游标。
    :param ui_event_seq: AG-UI 事件游标。
    :param state_epoch: 写入时的状态回写代次。
    """
    # 和回收拿同一把会话锁：回收要按顺序挑出最老的几个删掉，不能和这里的写入交错。
    with transaction.atomic():
        _lock_conversation(conversation_id)
        ConversationCheckpoint.objects.update_or_create(
            conversation_id=conversation_id,
            commit=commit,
            defaults={
                "run_id": run_id,
                "tag": tag,
                "context_version": context_version,
                "completed": completed,
                "log_seq": log_seq,
                "ui_event_seq": ui_event_seq,
                "state_epoch": state_epoch,
            },
        )


def latest(conversation_id: Any) -> ConversationCheckpoint | None:
    """返回这个会话最新的检查点，也就是冷启动时用来恢复工作区的那一个。

    「最新」指最后登记的那个，见 :meth:`ConversationCheckpointManager.newest_first`。

    :param conversation_id: 要恢复的会话。
    :return: 检查点行，没有则 ``None``。
    """
    return ConversationCheckpoint.objects.newest_first(conversation_id).first()


def reclaim(conversation_id: Any) -> Reclaimed:
    """把一个会话攒下的历史裁回保留策略允许的范围。

    检查点和上下文版本各自只留最近 N 个，互不牵制：检查点不引用上下文版本，冷启动也只读最新一版
    上下文。

    :param conversation_id: 要回收的会话。
    :return: 这次各删掉了多少。
    """
    with transaction.atomic():
        _lock_conversation(conversation_id)
        return Reclaimed(
            checkpoints=_reclaim_checkpoints(conversation_id),
            versions=_reclaim_versions(conversation_id),
        )


def _lock_conversation(conversation_id: Any) -> None:
    """Serialize checkpoint registration and retention for one conversation."""
    Conversation.objects.select_for_update().only("pk").get(pk=conversation_id)


def _reclaim_checkpoints(conversation_id: Any) -> int:
    """删掉排在最近 N 个之外的检查点。

    排序和 :func:`latest` 一致，所以留下的永远是最后登记的那几个，冷启动要用的那一个必然在内。

    :param conversation_id: 要回收的会话。
    :return: 删掉的检查点数。
    """
    doomed = list(
        ConversationCheckpoint.objects.newest_first(conversation_id).values_list("pk", flat=True)[checkpoints_kept() :]
    )
    if not doomed:
        return 0

    ConversationCheckpoint.objects.filter(pk__in=doomed).delete()
    logger.info("Reclaimed %d checkpoint(s) of conversation %s", len(doomed), conversation_id)
    return len(doomed)


def _reclaim_versions(conversation_id: Any) -> int:
    """删掉不在最近 N 版之内的上下文版本。

    先删行再删 blob。反过来的话，一次失败的远端删除会留下一行指向已经不存在的文档，而那正好是
    冷启动最没法处理的状态——行说有，读出来没有。孤儿 blob 只是占空间。

    :param conversation_id: 要回收的会话。
    :return: 删掉的版本数。
    """
    # 版本号降序取前 N 个，所以 recent 的第一个就是最新那一版，也就是 load_context 会读的那一
    # 版。versions_kept() 被抬到至少 1，它必然落在这个集合里——「最新版永远不会被回收」这个不变
    # 量就是这么来的，不需要再额外挡一道。
    recent = set(
        ConversationContextVersion.objects.filter(conversation_id=conversation_id)
        .order_by("-context_version")
        .values_list("context_version", flat=True)[: versions_kept()]
    )
    doomed = list(
        ConversationContextVersion.objects.filter(conversation_id=conversation_id).exclude(context_version__in=recent)
    )
    if not doomed:
        return 0

    ConversationContextVersion.objects.filter(pk__in=[row.pk for row in doomed]).delete()
    for row in doomed:
        try:
            row.get_blob_store().delete()
        except Exception:
            # 每种失败的处理都一样：行已经没了，没人能再够到这个 blob；留着只是占空间。
            logger.exception(
                "Could not delete the blob of context version %d of conversation %s",
                row.context_version,
                conversation_id,
            )
    logger.info("Reclaimed %d context version(s) of conversation %s", len(doomed), conversation_id)
    return len(doomed)


def reclaim_quietly(conversation_id: Any) -> None:
    """回收过期的检查点与上下文版本，失败只记日志。

    给归档路径用：上下文这时已经写完了，把清理的失败变成这次写入的失败，只会让 Runtime 去重推一
    份已经存好的文档。

    挂在归档路径上，是因为「又推了一版上下文」正是历史开始变长的那一刻，也是唯一一个每轮都必然
    经过、又不在 SSE 流上的位置。

    :param conversation_id: 要回收的会话。
    """
    try:
        reclaim(conversation_id)
    except Exception:
        # 清理的任何失败都不该让一次成功的归档变成失败。
        logger.exception("Could not reclaim the old state of conversation %s", conversation_id)


arecord = sync_to_async(record)
alatest = sync_to_async(latest)
