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
* context 只有最新一版有意义，所以一个会话一行，文档本身落 blob 存储（一份 context 可能有好几
  MB，不适合塞进 MySQL 行里）。
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


class ConversationContextSnapshot(TimestampedModel):
    """一个会话最新一版的可信上下文，也就是冷启动唯一能依赖的东西。

    只留最新版：``SummarizingCompaction`` 是一次不可重放的真实 LLM 调用，所以上下文既没法从原始
    记录拼出来，历史版本也没有谁会去读——下一轮 run 要的永远是最后那一版。

    文档本身不落库，落 blob 存储；这张行记的是「哪一版」和「放在哪」。backend 与 config 记在行上
    而不是每次都从配置读，是为了部署改了存储配置之后，已经写出去的 blob 还找得回来。
    """

    conversation = models.OneToOneField(
        "conversations.Conversation",
        verbose_name="所属会话",
        on_delete=models.CASCADE,
        related_name="context_snapshot",
        primary_key=True,
    )
    context_version = models.PositiveIntegerField(verbose_name="上下文版本", default=0)
    # 当前支持 host_tmp_path 与 bk_repo，实际取值校验由 make_blob_store 负责。
    backend = models.CharField(verbose_name="存储引擎", max_length=32)
    config = models.JSONField(
        verbose_name="存储引擎配置",
        default=dict,
        help_text=(
            'HostTmpPath 使用 {"path": "/var/lib/app-spark/contexts/<uuid>.json"}，'
            'BkRepo 使用 {"bucket": "app-spark", "key": "conversations/<uuid>/context.json"}'
        ),
    )

    def get_blob_store(self) -> BlobStore:
        """构造这一份上下文文档实际存放位置的 blob 存储。

        :return: 已校验的 blob 存储。
        :raises StorageConfigurationError: 引擎未知或配置结构不对。
        """
        return make_blob_store(self.backend, self.config)
