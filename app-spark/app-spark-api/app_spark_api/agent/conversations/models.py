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

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import models, transaction
from django.db.models import F

from app_spark_api.agent.conversations.state_models import (
    ConversationContextSnapshot,
    ConversationMessage,
    ConversationUiEvent,
)
from app_spark_api.core.tenant.fields import tenant_id_field_factory
from app_spark_api.utils.models import OwnerTimestampedModel

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project

# Django 只会 import `<app>.models`，所以拆出去的状态表必须从这里能够到，否则不会被注册。
# 它们通过字符串引用 Conversation，因此这个方向的 import 不会成环。
__all__ = [
    "Conversation",
    "ConversationContextSnapshot",
    "ConversationManager",
    "ConversationMessage",
    "ConversationNumber",
    "ConversationQuerySet",
    "ConversationUiEvent",
]


class ConversationNumber(models.Model):
    """每个 Project 一行，记录这个 Project 已经发出去的最大会话序号。

    单独用一张计数器表，而不是每次取 ``MAX(number) + 1``，是因为后者有两个毛病：

    * 并发下会撞号——两个请求各自读到同一个最大值，然后都想用它 + 1；
    * 会话被删掉之后号码会被重发一次，之前分享出去的链接就指到别的会话上了。

    行的生死跟着 Project 走：建 Project 时由 signal 一并备好（见
    :mod:`~app_spark_api.agent.conversations.signals`），删 Project 时随外键级联消失。
    所以取号的时候可以直接假定它在，不必每次先去确认一遍。
    """

    project = models.OneToOneField(
        "projects.Project",
        verbose_name="所属项目",
        on_delete=models.CASCADE,
        related_name="conversation_number",
        primary_key=True,
    )
    last_number = models.PositiveIntegerField(verbose_name="已发放的最大序号", default=0)

    @classmethod
    def take_next(cls, project_id: str) -> int:
        """取走这个 Project 的下一个序号。

        :param project_id: 要取号的 Project。
        :return: 分配到的序号，从 1 开始。
        :raises ConversationNumber.DoesNotExist: 计数器行不存在。正常情况下不会发生。
        """
        if not transaction.get_connection().in_atomic_block:
            raise RuntimeError("take_next() 必须在事务里调用，否则行锁会在读回序号之前就放掉。")

        # 用一条 `UPDATE ... last_number + 1` 推进，而不是「读出来、加一、写回去」：加法在
        # 数据库里做，这条语句本身就把行锁拿到手了，一直持有到事务提交。于是同一个 Project
        # 的并发取号在这里排成一队，后面那句 SELECT 读到的必然是本事务刚写进去的值。
        if not cls.objects.filter(project_id=project_id).update(last_number=F("last_number") + 1):
            raise cls.DoesNotExist(f"Project {project_id} has no conversation number counter")
        return cls.objects.values_list("last_number", flat=True).get(project_id=project_id)


class ConversationQuerySet(models.QuerySet["Conversation"]):
    """Conversation 的查询集"""

    def live(self) -> "ConversationQuerySet":
        """只留下还活着的会话，也就是尚未被结束、还可以继续推进的那些。"""
        return self.filter(closed_at__isnull=True)

    def closed(self) -> "ConversationQuerySet":
        """只留下已经结束的会话。它们的历史仍可读，但不能再推进。"""
        return self.filter(closed_at__isnull=False)


class ConversationManager(models.Manager["Conversation"]):
    """Conversation 的管理器，建会话必须走这里，序号才有人发。"""

    def get_queryset(self) -> ConversationQuerySet:
        return ConversationQuerySet(self.model, using=self._db)

    def for_project(self, project: Project, *, is_live: bool | None = None) -> ConversationQuerySet:
        """列出一个 Project 的会话，按创建时间倒序。

        :param project: 要列出会话的 Project。
        :param is_live: ``True`` 只要还活着的，``False`` 只要已结束的，``None``（默认）全都要。
        :return: 排好序、尚未取值的 queryset，翻页交给调用方。
        """
        queryset = self.get_queryset().filter(project=project)
        if is_live is True:
            queryset = queryset.live()
        elif is_live is False:
            queryset = queryset.closed()
        return queryset.order_by("-created", "-number")

    def create_for_project(self, project: Project, *, owner: str | None) -> Conversation:
        """建一个会话，并给它分配所属 Project 内的下一个序号。

        取号和建行在同一个事务里：中间失败的话号也一并回滚，不会留下一个用掉但没人认领的
        号码。

        :param project: 会话所属的 Project。
        :param owner: 建会话的用户 pk。
        :return: 已经落库的会话。
        """
        with transaction.atomic():
            number = ConversationNumber.take_next(project.pk)
            return self.create(
                project=project,
                number=number,
                owner=owner,
                tenant_id=project.tenant_id,
            )


class Conversation(OwnerTimestampedModel):
    """一次由 Agent 驱动的 Project 开发会话，对应 Agent Runtime 里的一个 conversation。

    这张表只回答「这个 Project 有哪些会话」。会话内容本身在旁边的三张状态表里——消息历史、
    AG-UI 事件、上下文都由 Runtime 后台回写过来（见
    :mod:`~app_spark_api.agent.conversations.state_models`）。Runtime 自己的状态目录是可丢弃的
    本地缓冲，不是权威副本。

    Runtime 的 workspace 与状态目录也不落库，而是由 provider 的配置按 project_id 与
    conversation_id 确定性推导出来。等到 provisioning 不再确定性（比如换成远程沙箱，地址由
    沙箱侧分配）时，再把地址落到这张表上。
    """

    # 同时就是 AG-UI 的 threadId 和 Agent Runtime 的 conversation_id：一个会话在三处是同一个
    # 标识，中间没有映射表。
    id = models.UUIDField(verbose_name="会话 ID", primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="所属项目",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    # 对外露出的是它而不是上面的 UUID：URL 里 `/conversations/3/` 比一串 36 位的十六进制好认、
    # 好念、也好在日志和工单里对齐。UUID 仍然是这个会话的身份，只是不必让人去读它。
    number = models.PositiveIntegerField(verbose_name="会话序号")

    # Runtime 回写状态用的 token 里带着这个值，吊销就 +1，于是之前签发的全部作废。
    # token 本身没有过期时间——一个 Runtime 可能在两轮对话之间空转很久，让 token 自己过期只会把
    # 「暂停的会话」变成「丢掉的会话」——所以吊销必须是显式的，这个字段就是那个开关。它存在的
    # 理由是本服务并不能真的保证「一个会话只有一个 Runtime 在写」：进程句柄只在内存里，重启之后
    # 上一代残留的 Runtime 手里那张 token 依然有效。
    state_epoch = models.PositiveIntegerField(verbose_name="状态回写授权代次", default=1)

    # 会话的生命周期就这一个字段：null 表示还活着（live），有值表示已经结束。
    #
    # 之所以落库，而不是拿「当前有没有 Runtime 在跑」当作 live：Runtime 是可丢弃的，进程句柄
    # 只在内存里（见 local provider 的注释），本服务一重启就全没了。用它当 live 的话，同一个
    # 会话会因为一次无关的重启从 live 变成非 live，而下一轮对话又会把它变回来——这种会自己反复
    # 翻转的状态没法当契约用，也没法回答「这个会话是不是已经被用户结束了」。
    closed_at = models.DateTimeField(verbose_name="结束时间", null=True, default=None)

    tenant_id = tenant_id_field_factory(db_index=False)

    objects = ConversationManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "number"], name="uniq_conversation_number_per_project"),
        ]
        indexes = [models.Index(fields=["project", "-created"])]

    @property
    def is_live(self) -> bool:
        """这个会话是否还活着，也就是还能不能继续推进。"""
        return self.closed_at is None
