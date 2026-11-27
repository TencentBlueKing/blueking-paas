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
from typing import Annotated, Any, Self
from uuid import UUID

from ninja import Field, Schema
from pydantic import StringConstraints, model_validator

from app_spark_api.agent.runtime.entities import AskUserAnswerInput, AskUserResponseInput, PendingQuestion

# 用户单轮输入的字符上限。
#
# 必须在这里单独设限，不能靠请求体的大小兜底：``DATA_UPLOAD_MAX_MEMORY_SIZE`` 被 Runtime 的状态
# 回写抬到了 64MB（见 settings），而那是给内部接口用的额度。
#
# 32K 字符对一次对话输入是很宽的（贴一整份报错日志也够），同时远小于 Agent 侧一份 context 的压缩
# 预算（COMPACTION_TARGET_TOKENS，480,000 token），不会先于压缩成为瓶颈。
MAX_RUN_CONTENT_LENGTH = 32 * 1024

# 模型 ID 的长度上限。
MAX_MODEL_ID_LENGTH = 128

# 一轮对话最多引用几个附件，与前端一致。
MAX_ATTACHMENTS_PER_RUN = 3


# ------------------------------------------------------------------------------
# Ask-User（结构化提问与回答）相关 Schema
# ------------------------------------------------------------------------------


class AskUserOptionSchema(Schema):
    """结构化提问中的一个候选项。"""

    label: str = Field(description="选项文案")
    description: str = Field(default="", description="选项说明")


class AskUserQuestionSchema(Schema):
    """结构化提问中的一道问题。"""

    header: str = Field(description="问题短标题，提交回答时按此匹配")
    question: str = Field(description="完整问题正文")
    options: list[AskUserOptionSchema] = Field(description="候选项列表")
    multi_select: bool = Field(default=False, description="是否允许多选")


class PendingQuestionSchema(Schema):
    """一次挂起等待用户回答的 ask_user_question 工具调用。"""

    tool_call_id: str = Field(description="挂起的工具调用 ID")
    questions: list[AskUserQuestionSchema] = Field(description="待回答的问题列表")

    @classmethod
    def from_runtime(cls, item: PendingQuestion) -> Self:
        """Convert a Runtime-layer :class:`PendingQuestion` into an API response schema."""
        return cls(
            tool_call_id=item.tool_call_id,
            questions=[
                AskUserQuestionSchema(
                    header=question.header,
                    question=question.question,
                    options=[
                        AskUserOptionSchema(label=option.label, description=option.description)
                        for option in question.options
                    ],
                    multi_select=question.multi_select,
                )
                for question in item.questions
            ],
        )


class AskUserAnswerSchema(Schema):
    """对单道结构化提问的回答：选择候选项或填写自定义回答。"""

    header: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        description="对应提问中的 header"
    )
    selected: list[str] = Field(default_factory=list, description="选中的候选项 label 列表")
    custom_answer: str | None = Field(
        default=None,
        max_length=MAX_RUN_CONTENT_LENGTH,
        description="自定义回答文本；与 selected 互斥",
    )


class AskUserResponseSchema(Schema):
    """对一次挂起 ask_user_question 调用的完整回答。"""

    tool_call_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        description="挂起的工具调用 ID"
    )
    answers: list[AskUserAnswerSchema] = Field(default_factory=list, description="各问题的回答列表")
    cancelled: bool = Field(default=False, description="是否跳过/取消回答；为 true 时 answers 必须为空")

    def to_runtime_input(self) -> AskUserResponseInput:
        """Convert this request schema to the Runtime client's input value object."""
        return AskUserResponseInput(
            tool_call_id=self.tool_call_id,
            answers=tuple(
                AskUserAnswerInput(
                    header=answer.header,
                    selected=tuple(answer.selected),
                    custom_answer=answer.custom_answer,
                )
                for answer in self.answers
            ),
            cancelled=self.cancelled,
        )


# ------------------------------------------------------------------------------
# 会话、状态与历史相关 Schema
# ------------------------------------------------------------------------------


class ConversationResponse(Schema):
    """一个会话在列表里的样子，只有本服务库里的东西，不含任何 Runtime 的现状。

    列表刻意不报 Runtime 的现状（用什么模型、有没有在跑）。
    """

    number: int = Field(description="会话编号")
    conversation_id: UUID = Field(alias="id", description="会话全局唯一 ID，也是 AG-UI 事件里的 threadId")
    is_live: bool = Field(description="会话是否还活着（live），即是否还能继续推进")
    created_at: datetime = Field(description="会话创建时间")
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
    # 和 running 无关：run 早就结束了，用户拉起来的那个应用还在跑。
    dev_server_status: str | None = Field(
        description=(
            "活跃 Runtime 报的工作区应用 dev server 状态：not_started / starting / ready / stopped；"
            "没有活跃 Runtime、或 Runtime 没报时为 null"
        ),
    )
    replication_pending: bool = Field(
        description=(
            "是否有状态留在 Runtime 里没回写过来。要判断某一轮会话是否真的落库，"
            "必须 running 与本字段同时为 false——由于 flush 超时也会释放 run guard，"
            "所以单看 running=false 并不代表这一轮已经在库里"
        )
    )
    # 停一轮要点名，刷新页面后的客户端手里没有 SSE 里的 runId，只能从这里拿。
    run_id: str | None = Field(
        default=None,
        description=(
            "活跃 Runtime 上正在跑的那一轮的 run ID，即停止接口要的 run_id；"
            "没有在跑的一轮时为 null，一轮刚被接受、还在准备时也可能短暂为 null"
        ),
    )
    # 运行环境空闲回收、Agent 退出或到了最长存活期之后，下一轮要先花几十秒准备，前端靠它提前提示。
    runtime_ready: bool = Field(
        description=(
            "是否有可直接复用的运行环境；为 false 时下一轮对话需要先准备运行环境"
            "（首次对话、空闲回收后、Agent 不可用或到达最长存活期）"
        )
    )
    pending_questions: list[PendingQuestionSchema] = Field(
        default_factory=list,
        description="当前挂起等待用户回答的结构化提问列表；没有待回答提问或没有活跃 Runtime 时为空列表",
    )


class PreviewResponse(Schema):
    """会话里那个工作区应用该去哪儿打开，以及此刻打不打得开。

    地址和状态是两回事，所以分成两个字段。没有可直连的沙箱时，origin 是本服务上的反代路径，按
    本次请求的 Host 签发，会话一建好就有。远程沙箱拉起后，origin 是 get_host 查回来的暴露域名，
    每次现查，沙箱重建后跟着变。dev_server_status 说的是这一刻沙箱里那个进程能不能服务。前端据此
    决定是先摆一个占位还是直接把 iframe 挂上去，而不是靠 URL 有没有值来猜。
    """

    origin: str = Field(
        description=(
            "用 iframe 打开工作区应用的地址，末尾带斜杠。"
            "direct 为 false 时是本服务上的反代路径，按本次请求的 Host 签发；"
            "为 true 时是远程沙箱的暴露域名，沙箱重建后会变"
        ),
    )
    direct: bool = Field(
        description="origin 是否是沙箱暴露的主机，由浏览器直接打开；false 表示经本服务反代",
    )
    dev_server_status: str | None = Field(
        description=(
            "活跃 Runtime 报的工作区应用 dev server 状态：not_started 还没拉起过；"
            "starting 进程在跑但还答不出，继续等；ready 可以挂 iframe 了；stopped 进程没了。"
            "null 表示此刻问不到——没有活跃 Runtime，或者有但联系不上"
        ),
    )


class PreviewStartResponse(Schema):
    """拉起预览的请求已经交给 Runtime；应用是否起来了不在这里等。"""

    outcome: str = Field(
        description=(
            "starting：已在拉起，或本来就在跑，之后看预览接口的 dev_server_status；"
            "no_project：工作区里还没有可启动的项目，模型写出代码后会自己拉起，不是错误"
        ),
    )


class RunStopResponse(Schema):
    """停止请求已经交给 Runtime，这一轮正在收尾。"""

    run_id: str = Field(description="被请求停止的那一轮")


class AttachmentResponse(Schema):
    """会话里的一个文件附件。"""

    id: UUID = Field(description="附件 ID，发起一轮对话时放进 attachment_ids")
    filename: str = Field(description="上传时的文件名，仅用于展示")
    mime_type: str = Field(description="按内容识别为主、扩展名为辅得出的文件类型；image/ 开头时前端可以预览")
    size: int = Field(description="字节数")
    url: str = Field(description="读取文件内容的地址，需要登录态，不会过期；图片可直接用作 img 的 src")
    created_at: datetime = Field(description="上传时间")


class StartRunRequest(Schema):
    """推进一次会话交互的请求体。

    仅包含本次需要发送的新信息：普通消息（``content`` / ``attachment_ids``）或结构化提问的回答
    （``ask_user_responses``），两者互斥。Runtime 中已经有了历史，重复发送会导致冲突。
    """

    content: str = Field(
        "",
        max_length=MAX_RUN_CONTENT_LENGTH,
        description="用户本轮发送的内容；带了附件或提交提问回答时可以为空，否则不能为空",
    )
    attachment_ids: list[UUID] = Field(
        default_factory=list,
        max_length=MAX_ATTACHMENTS_PER_RUN,
        description=(
            "本轮引用的文件附件，取自上传附件接口返回的 id，每个只能随一轮发出。"
            "其中有图片而所选模型不支持图片时返回 422 MODEL_IMAGE_INPUT_UNSUPPORTED"
        ),
    )
    ask_user_responses: list[AskUserResponseSchema] = Field(
        default_factory=list,
        description="回答挂起的结构化提问并恢复 Agent；不能与 content 或 attachment_ids 同时提供",
    )
    # 先去掉首尾空白再量长度：纯空白在这里就是 422，带空格的 ID 也不会原样转发给网关。
    model_id: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MODEL_ID_LENGTH)] | None
    ) = Field(
        None,
        description=(
            "本轮使用的模型 ID，取自模型列表接口的 models[].id；不传则用沙箱默认模型。"
            "不在可选列表里、或 direct 来源下不是内置模型时返回 422 MODEL_NOT_AVAILABLE"
        ),
    )

    @model_validator(mode="after")
    def check_has_input(self) -> Self:
        has_user_input = bool(self.content.strip()) or bool(self.attachment_ids)
        has_ask_user = bool(self.ask_user_responses)
        if has_user_input and has_ask_user:
            raise ValueError("ask_user_responses cannot be combined with content or attachment_ids")

        # 纯空白和空串一样算没说话：只发一个空格给模型，换来的只会是一句「请问有什么可以帮你」。
        if not has_user_input and not has_ask_user:
            raise ValueError("content, attachment_ids, and ask_user_responses cannot all be empty")

        # 同一个附件在一轮里出现两次，模型会以为用户发了两份，绑定时也只会记一次。
        if len(set(self.attachment_ids)) != len(self.attachment_ids):
            raise ValueError("attachment_ids contains duplicates")

        return self


class UiEventRecord(Schema):
    """AG-UI 事件记录，保持 Runtime 与 ui-events 接口已有的传输结构。"""

    seq: int
    run_id: str
    timestamp: str = Field(description="Runtime 记录事件的 ISO 8601 时间，保留原有精度和格式")
    event: dict[str, Any]


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
    records: list[UiEventRecord] = Field(description="AG-UI 事件记录，原样透传")


class UserMessageHistoryRecord(Schema):
    """历史中的一条用户输入。"""

    id: int = Field(description="用户消息 ID，可用于去重")
    run_id: str | None
    after_seq: int = Field(description="插在该 UI event 序号之后，0 表示所有事件之前")
    created_at: datetime
    content: str
    attachments: list[AttachmentResponse] = Field(default_factory=list, description="随这条输入发出的文件附件")


class ConversationHistoryRecord(Schema):
    """一条展示历史：两个字段恰好一个非空，分别复用各自的记录结构。"""

    ui_event: UiEventRecord | None = None
    user_message: UserMessageHistoryRecord | None = None


class ConversationHistoryResponse(Schema):
    """一页展示历史，用户输入按创建时保存的 after_seq 定位。"""

    records: list[ConversationHistoryRecord] = Field(description="本页记录，按对话正序排列")
    next_cursor: str | None = Field(description="取更早一页时原样回传；null 表示已经到会话开头，没有更早的内容了")
    # 「到会话开头了」和「最新一轮还没回写完」是两件事：前者看 next_cursor，后者看
    # `RuntimeStateResponse.replication_pending`。这个字段是给后者用的水位。
    last_seq: int = Field(description="AG-UI 事件频道当前的最后一个游标")
