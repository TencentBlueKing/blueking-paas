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

"""会话状态的持久化落点：Agent Runtime 推上来的三类数据在这一侧的样子。

这些表存在的理由只有一个：让 Runtime 变成可丢弃的。Runtime 自己的状态目录会跟着容器一起消失，
所以「这个会话到底发生过什么」必须在这边有一份，否则会话冷启动只是换一次进程，不是真的冷启动。

三类数据按各自的读法分开落：

* 两条 append-only 频道各自一张表。分表而不是加一个 channel 字段，是因为原始对话记录的体量比
  AG-UI 事件大一个量级、读路径也完全不同——前端翻页读的是事件，原始记录只在排查和审计时才碰。
  混在一张表里会让前端翻页的热索引和大块冷数据抢同一批页面；分开之后，将来把原始记录搬去 blob
  存储也是原地替换。
* context 一版一行，文档本身落 blob 存储（一份 context 可能有好几 MB，不适合塞进 MySQL 行
  里）。「最新一版」不额外记一个指针，就是版本号最大的那一行——多一个指针就多一个会和版本行
  说法不一致的地方，而它能回答的问题版本行本来就能回答。
"""

from __future__ import annotations

from django.db import models

from app_spark_api.repository.storage.blob_stores import BlobStore, make_blob_store
from app_spark_api.utils.models import TimestampedModel


class ConversationChannelRecord(models.Model):
    """一条从 Runtime 复制过来的 append-only 频道记录。

    字段与 Runtime 侧 ``LogRecord`` 一一对应，因为它就是原样搬过来的：``payload`` 不做解析，
    本服务不需要认识模型消息或 AG-UI 事件的内部结构。

    ``seq`` 在一个会话内全局连续，跨 Runtime 世代也连续——冷启动时控制面会把当前游标播种给新
    Runtime，让它接着往下编号，而不是从 1 重新开始。所以 ``(conversation, seq)`` 唯一约束既是
    幂等写入的依据（重复推送直接被约束挡掉），也是前端翻页的游标。
    """

    seq = models.PositiveIntegerField(verbose_name="会话内序号")
    # 不用 UUIDField：这是 Runtime 侧的标识，其取值规则属于 Runtime 的实现细节，本表只负责原样
    # 保留，不去替它约束格式。
    run_id = models.CharField(verbose_name="产生这条记录的 run", max_length=64)
    payload = models.JSONField(verbose_name="记录内容，原样透传")
    recorded_at = models.DateTimeField(verbose_name="Runtime 侧记录该条目的时间")

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(fields=["conversation", "seq"], name="uniq_%(class)s_seq"),
        ]


class ConversationMessage(ConversationChannelRecord):
    """原始对话记录：真正发给模型、以及模型返回的每一条消息。

    对冷启动不是必需的（那只需要 context），存在的意义是排查与审计。也正因为如此，它是三类数据
    里最先该被挪走的：体量最大、查询最少。
    """

    conversation = models.ForeignKey(
        "conversations.Conversation",
        verbose_name="所属会话",
        on_delete=models.CASCADE,
        related_name="messages",
    )

    class Meta(ConversationChannelRecord.Meta):
        pass


class ConversationUiEvent(ConversationChannelRecord):
    """AG-UI 事件历史：客户端当时看到的那一串事件，delta 已经在 Runtime 侧合并过。

    这是「点开一个历史会话能看到内容」的唯一来源。SSE 本身没有重放能力，而事件里的 message id
    是每次流式输出随机生成的，没法从模型历史里反推——所以只能存下来。
    """

    conversation = models.ForeignKey(
        "conversations.Conversation",
        verbose_name="所属会话",
        on_delete=models.CASCADE,
        related_name="ui_events",
    )

    class Meta(ConversationChannelRecord.Meta):
        pass


class ConversationContextVersion(TimestampedModel):
    """一个被保留下来的上下文版本，以及它自己那份 blob 放在哪。

    上下文没法从原始记录重放出来——``SummarizingCompaction`` 是一次真实的 LLM 调用——所以这里存
    的就是冷启动唯一能依赖的东西。

    一版一行、一版一份 blob（key 里带版本号），而不是就地覆盖一份「最新的」：检查点要的不是最新
    版，而是**和某个 commit 配套的那一版**。文件和会话必须描述同一个时刻，否则恢复出来的
    Runtime 会拿着记得别的文件的模型继续写代码。覆盖式的 blob 只能回答「最新是什么」。

    普通冷启动要的「最新一版」，就是这张表里版本号最大的那一行，没有另外的指针。

    backend 与 config 记在行上而不是每次从配置推，是为了部署改了存储配置之后，已经写出去的 blob
    还找得回来。

    保留是有限的，见 :mod:`app_spark_api.agent.conversations.checkpoints` 的回收逻辑：只留被留存
    下来的检查点引用的版本，加上最近若干版。否则 blob 存储会无上限增长。
    """

    conversation = models.ForeignKey(
        "conversations.Conversation",
        verbose_name="所属会话",
        on_delete=models.CASCADE,
        related_name="context_versions",
    )
    context_version = models.PositiveIntegerField(verbose_name="上下文版本")
    # 当前支持 host_tmp_path 与 bk_repo，实际取值校验由 make_blob_store 负责。
    backend = models.CharField(verbose_name="存储引擎", max_length=32)
    config = models.JSONField(verbose_name="存储引擎配置", default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "context_version"],
                name="uniq_conversation_context_version",
            )
        ]
        indexes = [models.Index(fields=["conversation", "-context_version"])]

    def get_blob_store(self) -> BlobStore:
        """构造这一版上下文实际存放位置的 blob 存储。

        :return: 已校验的 blob 存储。
        :raises StorageConfigurationError: 引擎未知或配置结构不对。
        """
        return make_blob_store(self.backend, self.config)


class ConversationCheckpoint(TimestampedModel):
    """一个可恢复点：某个 commit、钉住它的 tag，以及配套的上下文版本和日志游标。

    这里存在只说明一半：Runtime 保证了 commit 和 tag 已经到远端。另一半——控制面手上真的存着
    ``context_version`` 那一版上下文——由 :func:`~app_spark_api.agent.conversations.checkpoints.
    restorable_checkpoints` 查出来，不落成字段。计划里明确要求「代码已推送、上下文尚未保存」和
    反过来的情况都不能被误判成完整恢复点。

    ``state_epoch`` 一并记下，是为了后续阶段校验写入者租约。这里复用既有的代次概念，不另起一个
    并行的计数器。

    行本身很小，但每一行都钉住一版上下文不让回收，所以检查点也是有保留上限的：只留最近若干个，
    见 :mod:`app_spark_api.agent.conversations.checkpoints` 的回收逻辑。
    """

    conversation = models.ForeignKey(
        "conversations.Conversation",
        verbose_name="所属会话",
        on_delete=models.CASCADE,
        related_name="checkpoints",
    )
    run_id = models.CharField(verbose_name="产生该检查点的 run", max_length=64)
    # 40 位十六进制的 SHA-1；给 SHA-256 仓库留出余量。
    commit = models.CharField(verbose_name="仓库提交", max_length=64)
    tag = models.CharField(verbose_name="钉住该提交的远端 tag", max_length=255)
    context_version = models.PositiveIntegerField(verbose_name="配套的上下文版本")
    # 提交到达远端那一刻，两条频道各自存到了哪。记的是**当时的位置**，供排查「这个检查点落后
    # 了多少」用；冷恢复给新 Runtime 的游标不取自这里，取的是恢复那一刻的真实位置——频道只增不
    # 删，从一个旧位置续写只会撞上已经存在的序号。理由见 services._resume_if_cold。
    log_seq = models.PositiveIntegerField(verbose_name="原始记录游标", default=0)
    ui_event_seq = models.PositiveIntegerField(verbose_name="AG-UI 事件游标", default=0)
    state_epoch = models.PositiveIntegerField(verbose_name="写入时的状态回写代次", default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "commit"],
                name="uniq_conversation_checkpoint_commit",
            )
        ]
        # 冷恢复只问一个问题：这个会话最新的可恢复点是哪个。
        indexes = [models.Index(fields=["conversation", "-created"])]
