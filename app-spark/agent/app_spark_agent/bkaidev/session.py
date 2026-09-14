"""对话中间层：用已有三份持久化，经 AidevApiClient 调 bkaidev。

磁盘契约不变，文件名也不是配置项。context.json 是发给模型的可信历史
（ContextStore），压缩会整体替换它。log.jsonl 是原始对话记录（AppendLog，
payload_key=message）。ui_events.jsonl 是客户端看到的 AG-UI 事件（AppendLog，
payload_key=event）。

本层只读这三份来定位会话，不改写 context.json（压缩后的权威历史仍由
Agent / TranscriptRecorder 提交），也不往 log.jsonl 写 OpenAI 原始报文——
transcript 的 payload 形状是 pydantic-ai ModelMessage。
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app_spark_agent import settings
from app_spark_agent.bkaidev.client import AidevApiClient
from app_spark_agent.bkaidev.messages import openai_messages_from_model_messages
from app_spark_agent.bkaidev.types import (
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    FunctionTool,
)
from app_spark_agent.state import AppendLog, ContextStore, ConversationContext


@dataclass(frozen=True)
class SessionCursors:
    """三份持久化当前能读到的游标，和 GET /health 对齐。"""

    conversation_id: str | None
    context_version: int
    log_seq: int
    ui_event_seq: int


@dataclass(frozen=True)
class ConversationSession:
    """把一次网关调用接到当前 Runtime 的会话状态上。

    :param client: 已带好 access_token 的网关客户端。
    :param context_store: context.json。
    :param transcript: log.jsonl。
    :param ui_events: ui_events.jsonl。
    """

    client: AidevApiClient
    context_store: ContextStore
    transcript: AppendLog
    ui_events: AppendLog

    @property
    def context(self) -> ConversationContext:
        """当前已提交的可信历史。"""
        return self.context_store.context

    @property
    def cursors(self) -> SessionCursors:
        """三份持久化当前的游标，供控制面或排障对照 health。"""
        context = self.context
        return SessionCursors(
            conversation_id=context.conversation_id,
            context_version=context.context_version,
            log_seq=self.transcript.last_seq,
            ui_event_seq=self.ui_events.last_seq,
        )

    def history(self) -> list[ChatCompletionMessage]:
        """从 context.json 取出将发给网关的消息，不读 log.jsonl。"""
        return openai_messages_from_model_messages(self.context.messages)

    async def create_completion(
        self,
        extra_messages: Sequence[ChatCompletionMessage] = (),
        *,
        model: str | None = None,
        tools: Sequence[FunctionTool] | None = None,
        temperature: float | None = None,
    ) -> ChatCompletionResponse:
        """用可信历史加上本轮增量，发一次非流式 chat/completions。

        :param extra_messages: 尚未写入 context 的本轮消息（通常是最新 user）。
        :param model: 覆盖 MODEL_NAME；默认用对照表里的注入名。
        :param tools: 本轮可供调用的函数。
        :param temperature: 覆盖协议默认温度。
        """
        request = ChatCompletionRequest(
            model=model or settings.resolved_model_name(),
            messages=[*self.history(), *extra_messages],
            tools=list(tools) if tools is not None else None,
            temperature=temperature,
        )
        return await self.client.create_chat_completion(request)
