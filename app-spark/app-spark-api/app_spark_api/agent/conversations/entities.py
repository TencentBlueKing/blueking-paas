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

from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Field, Schema


class ConversationResponse(Schema):
    """一个会话在列表里的样子，只有本服务库里的东西，不含任何 Runtime 的现状。

    列表刻意不报 Runtime 的现状（用什么模型、有没有在跑）。
    """

    number: int = Field(description="会话编号")
    conversation_id: UUID = Field(alias="id", description="会话全局唯一 ID，也是 AG-UI 事件里的 threadId")
    is_live: bool = Field(description="会话是否还活着（live），即是否还能继续推进")
    created: datetime = Field(description="会话创建时间")
    closed_at: datetime | None = Field(description="会话结束时间；仍然活着时为 null")


class RuntimeStateResponse(Schema):
    """一个会话，包含服务端的持久化状态如上下文版本、UI 事件游标等。

    本会话对话是持久化的值，和某个具体的 Agent 会话 Runtime（比如沙箱中）无关，一个会话可能
    会因为会话 Runtime 的重复拉齐而使用若干个 Runtime，但会话状态仅一份，会被持续推进。
    """

    number: int = Field(description="会话编号，按 Project 递增")
    # Kept alongside the number because AG-UI stamps every event with it: without it a client
    # has no way to tell which conversation an event belongs to.
    conversation_id: UUID = Field(description="会话全局唯一 ID，也是 AG-UI 事件里的 threadId")
    # 恢复一个历史会话时，客户端第一件要知道的事就是这个会话还能不能接着聊。少了它，唯一的
    # 发现方式就是发一轮对话然后吃一个 409。
    is_live: bool = Field(description="会话是否还活着（live），即是否还能继续推进")
    closed_at: datetime | None = Field(description="会话结束时间；仍然活着时为 null")
    model: str | None = Field(description="当前活跃的 Runtime 用的模型；没有 Runtime 时为 null")
    context_version: int = Field(description="已归档的上下文版本，同时也是冷启动恢复时使用的版本")
    log_seq: int = Field(description="原始对话记录的最后一个游标")
    ui_event_seq: int = Field(description="AG-UI 事件历史的最后一个游标")
    running: bool = Field(description="是否有活跃 Runtime 且正在执行 run")
    replication_pending: bool = Field(
        description=(
            "是否有状态留在 Runtime 里没回写过来。要判断某一轮会话是否真的落库，"
            "必须 running 与本字段同时为 false——由于 flush 超时也会释放 run guard，"
            "所以单看 running=false 并不代表这一轮已经在库里"
        )
    )


class StartRunRequest(Schema):
    """推进一次会话交互的请求体。

    仅包含本次需要发送的新信息：Runtime 中已经有了历史，如果重复发送会让会话中出现两种版本，进而
    导致冲突。
    """

    content: str = Field(min_length=1, description="用户本轮发送的内容")


class UiEventPageResponse(Schema):
    """
    一页 AG-UI 事件，这些事件都已从 Runtime 持久化到服务端中。

    客户端的 SSE 请求终止后基于这些事件来追赶进度：stream 本身无法重放，因此丢失的东西必须从已
    落库的历史中重新读回来；读的都是 api 服务端数据库表里的数据，而不是直接从 runtime 里读，因为
    包含历史事件 runtime 可能早就被销毁了。
    """

    # Because replication lands after the event stream ends, the newest events may briefly be
    # missing here. ``RuntimeStateResponse.replication_pending`` is what says so.

    since: int = Field(description="本页请求时使用的游标")
    last_seq: int = Field(description="频道当前的最后一个游标")
    exhausted: bool = Field(description="本页是否已经读到频道末尾")
    records: list[dict[str, Any]] = Field(description="AG-UI 事件记录，原样透传")
