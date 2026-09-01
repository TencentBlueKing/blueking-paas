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

from typing import Any
from uuid import UUID

from ninja import Field, Schema


class RuntimeStateResponse(Schema):
    """一个会话，以及本服务这边记着的它的状态。

    游标报的是本服务库里的值，不是某个 Runtime 文件里的值。Runtime 是可丢弃的，它的状态目录
    会跟着容器一起消失；而一个会话在库里永远是一条平坦的游标，前端翻页不需要知道它换过几代
    Runtime。
    """

    number: int = Field(description="会话在所属 Project 内的序号，URL 中使用")
    # Kept alongside the number because AG-UI stamps every event with it: without it a client
    # has no way to tell which conversation an event belongs to.
    conversation_id: UUID = Field(description="会话全局唯一 ID，也是 AG-UI 事件里的 threadId")
    model: str | None = Field(description="当前活着的 Runtime 用的模型；没有 Runtime 时为 null")
    context_version: int = Field(description="已归档的上下文版本，也是冷启动会恢复到的版本")
    log_seq: int = Field(description="原始对话记录的最后一个游标")
    ui_event_seq: int = Field(description="AG-UI 事件历史的最后一个游标")
    running: bool = Field(description="是否有 Runtime 活着且正在执行 run")
    replication_pending: bool = Field(
        description=(
            "是否还有状态留在 Runtime 里没回写过来。要判断某一轮是否真的落库，"
            "必须 running 与本字段同时为 false——flush 超时也会释放 run guard，"
            "所以单看 running=false 并不代表这一轮已经在库里"
        )
    )


class StartRunRequest(Schema):
    """One turn of a conversation.

    Only the new message: the Runtime owns the history, and resending it would give the two
    sides two versions of the same conversation to disagree about.
    """

    content: str = Field(min_length=1, description="用户这一轮说的话")


class UiEventPageResponse(Schema):
    """A page of the AG-UI events that have been replicated into this service.

    This is how a client that lost its SSE connection catches up: the stream itself cannot be
    replayed, so anything missed has to be read back from the stored history. Read from this
    service's own tables, never from a Runtime -- a conversation whose Runtime is long gone has
    to answer this just as well as one still in progress.

    Because replication lands after the event stream ends, the newest events may briefly be
    missing here. ``RuntimeStateResponse.replication_pending`` is what says so.
    """

    since: int = Field(description="本页请求时使用的游标")
    last_seq: int = Field(description="频道当前的最后一个游标")
    exhausted: bool = Field(description="本页是否已经读到频道末尾")
    records: list[dict[str, Any]] = Field(description="AG-UI 事件记录，原样透传")


class ErrorResponse(Schema):
    detail: str
