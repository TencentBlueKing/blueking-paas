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

"""可恢复点：把一次提交和它配套的会话上下文绑成一个能恢复的整体。

一个检查点要成立，两件事都得到位：

* Runtime 已经把 commit 和钉住它的 tag 推到远端；
* 控制面已经存下了配套的那一版上下文。

两件事从两条路、按不确定的先后到达这里。所以「可恢复」不做成一个由某条路径去置位的字段，而是
一个查询：检查点行存在（代码在远端）**且**它引用的那一版上下文行还在（记忆存着）。字段要两条
路径都记得去置位，还要防住「上下文刚好在检查点落库前后到达」的交错；查询没有这个时序。

反过来说，任一件没到位的中间态**不能**被当成恢复点。文件和记忆描述的不是同一个时刻时，恢复出
来的 Runtime 会拿着记得别的文件的模型继续写代码，而错误要到好几轮之后才看得出来。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import attrs
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef

from app_spark_api.agent.conversations.state_models import (
    ConversationCheckpoint,
    ConversationContextVersion,
)

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

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
    """除被引用版本外还要保留多少个最近的上下文版本。"""
    # 至少保留 1 个作为冷启动所使用的上下文
    return max(1, int(settings.AGENT_CONTEXT_VERSIONS_KEPT))


def checkpoints_kept() -> int:
    """一个会话保留多少个最近的检查点。

    同样抬到至少 1：一个检查点都不留，等于关掉工作区恢复。
    """
    return max(1, int(settings.AGENT_CHECKPOINTS_KEPT))


def restorable_checkpoints(conversation_id: Any) -> QuerySet[ConversationCheckpoint]:
    """返回这个会话所有「代码和上下文都在」的检查点。

    :param conversation_id: 要查的会话。
    :return: 过滤后的检查点查询集。
    """
    has_context = ConversationContextVersion.objects.filter(
        conversation_id=OuterRef("conversation_id"),
        context_version=OuterRef("context_version"),
    )
    return ConversationCheckpoint.objects.filter(conversation_id=conversation_id).filter(Exists(has_context))


def record(
    conversation_id: UUID,
    *,
    run_id: str,
    commit: str,
    tag: str,
    context_version: int,
    log_seq: int,
    ui_event_seq: int,
    state_epoch: int,
) -> bool:
    """记下一个 Runtime 报上来的检查点，并回答它现在是否已经可恢复。

    幂等：同一个 commit 重复上报会更新原行而不是新建一行。Runtime 在确认回执丢失时**必须**重报
    同一个检查点，而不是再做一次提交——代码已经在远端了，再提交只会多出一个内容相同的 SHA。

    :param conversation_id: 检查点所属会话。
    :param run_id: 产生这次提交的 run。
    :param commit: 已在远端的提交 SHA。
    :param tag: 钉住该提交的不可移动远端 tag。
    :param context_version: 和这次提交配套的上下文版本。
    :param log_seq: 原始记录游标。
    :param ui_event_seq: AG-UI 事件游标。
    :param state_epoch: 写入时的状态回写代次。
    :return: 该检查点此刻是否已可恢复。
    """
    with transaction.atomic():
        ConversationCheckpoint.objects.update_or_create(
            conversation_id=conversation_id,
            commit=commit,
            defaults={
                "run_id": run_id,
                "tag": tag,
                "context_version": context_version,
                "log_seq": log_seq,
                "ui_event_seq": ui_event_seq,
                "state_epoch": state_epoch,
            },
        )
    # 只问上下文行在不在，不去读 blob：这条路径在请求里，而 blob 可能在远端对象存储上。
    stored = ConversationContextVersion.objects.filter(
        conversation_id=conversation_id,
        context_version=context_version,
    ).exists()
    if not stored:
        logger.info(
            "Checkpoint %s of conversation %s is on the remote but its context version %d has "
            "not been archived yet, so it is not restorable",
            commit,
            conversation_id,
            context_version,
        )
    return stored


def latest_restorable(conversation_id: Any) -> ConversationCheckpoint | None:
    """返回这个会话最新的可恢复点。

    按上下文版本排序而不是按时间：版本号就是这个会话推进到了哪一步，而两个检查点的创建时间在同
    一次重试里可能挨得极近。

    :param conversation_id: 要恢复的会话。
    :return: 检查点行，没有则 ``None``。
    """
    return restorable_checkpoints(conversation_id).order_by("-context_version", "-created").first()


def reclaim(conversation_id: Any) -> Reclaimed:
    """把一个会话攒下的历史裁回保留策略允许的范围。

    两步，顺序不能反：先淘汰过老的检查点，再删没人要的上下文版本。检查点会钉住它引用的那一版，
    所以先删检查点，被它钉住的版本才能在**同一次**回收里一起走。反过来的话，每一版都要多熬一
    轮回收才轮得到自己，而在那之前它的 blob 一直占着地方。

    :param conversation_id: 要回收的会话。
    :return: 这次各删掉了多少。
    """
    return Reclaimed(
        checkpoints=_reclaim_checkpoints(conversation_id),
        versions=_reclaim_versions(conversation_id),
    )


def _reclaim_checkpoints(conversation_id: Any) -> int:
    """删掉排在最近 N 个之外的检查点。

    排序和 :func:`latest_restorable` 一致（先看上下文版本，同版本再看创建时间），所以留下的
    永远是这个会话推进得最远的那几个。这里不过滤可恢复性：一个还不可恢复的检查点，是因为它的
    上下文刚推过来还没落地，而它比所有可恢复的都新，本来就该留着。

    :param conversation_id: 要回收的会话。
    :return: 删掉的检查点数。
    """
    doomed = list(
        ConversationCheckpoint.objects.filter(conversation_id=conversation_id)
        .order_by("-context_version", "-created")
        .values_list("pk", flat=True)[checkpoints_kept() :]
    )
    if not doomed:
        return 0

    ConversationCheckpoint.objects.filter(pk__in=doomed).delete()
    logger.info("Reclaimed %d checkpoint(s) of conversation %s", len(doomed), conversation_id)
    return len(doomed)


def _reclaim_versions(conversation_id: Any) -> int:
    """删掉既没被检查点引用、也不在最近 N 版之内的上下文版本。

    先删行再删 blob。反过来的话，一次失败的远端删除会留下一行指向已经不存在的文档，而那正好是
    冷启动最没法处理的状态——行说有，读出来没有。孤儿 blob 只是占空间。

    :param conversation_id: 要回收的会话。
    :return: 删掉的版本数。
    """
    referenced = set(
        ConversationCheckpoint.objects.filter(conversation_id=conversation_id).values_list(
            "context_version", flat=True
        )
    )
    # 版本号降序取前 N 个，所以 recent 的第一个就是最新那一版，也就是 load_context 会读的那一
    # 版。versions_kept() 被抬到至少 1，它必然落在这个集合里——「最新版永远不会被回收」这个不变
    # 量就是这么来的，不需要再额外挡一道。
    recent = set(
        ConversationContextVersion.objects.filter(conversation_id=conversation_id)
        .order_by("-context_version")
        .values_list("context_version", flat=True)[: versions_kept()]
    )
    doomed = list(
        ConversationContextVersion.objects.filter(conversation_id=conversation_id).exclude(
            context_version__in=referenced | recent
        )
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
alatest_restorable = sync_to_async(latest_restorable)
