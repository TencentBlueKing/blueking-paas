"""把 Runtime 可信历史（pydantic-ai ModelMessage）转成网关 messages。

context.json 存的是压缩后仍会发给模型的历史，不能从 log.jsonl 拼回来。
本模块只做协议映射，不读写磁盘。
"""

from collections.abc import Sequence

from pydantic_ai import ModelMessage
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from app_spark_agent.bkaidev.types import ChatCompletionMessage, ChatMessageToolCall, FunctionCall


def openai_messages_from_model_messages(
    messages: Sequence[ModelMessage],
) -> list[ChatCompletionMessage]:
    """把 ConversationContext.messages 转成 Chat Completions 的 messages。"""
    converted: list[ChatCompletionMessage] = []
    for message in messages:
        if isinstance(message, ModelRequest):
            converted.extend(_from_request(message))
        elif isinstance(message, ModelResponse):
            converted.append(_from_response(message))
    return converted


def _from_request(message: ModelRequest) -> list[ChatCompletionMessage]:
    converted: list[ChatCompletionMessage] = []
    for part in message.parts:
        if isinstance(part, SystemPromptPart):
            converted.append(ChatCompletionMessage(role="system", content=_text(part.content)))
        elif isinstance(part, UserPromptPart):
            converted.append(ChatCompletionMessage(role="user", content=_text(part.content)))
        elif isinstance(part, ToolReturnPart):
            converted.append(
                ChatCompletionMessage(
                    role="tool",
                    content=_text(part.content),
                    tool_call_id=part.tool_call_id,
                    name=part.tool_name,
                )
            )
        elif isinstance(part, RetryPromptPart):
            converted.append(_from_retry(part))
        else:
            raise TypeError(f"unsupported model request part: {type(part).__name__}")
    return converted


def _from_retry(part: RetryPromptPart) -> ChatCompletionMessage:
    """工具校验失败必须回一条配对的 role=tool，否则网关会 400。"""
    if part.tool_name:
        return ChatCompletionMessage(
            role="tool",
            content=part.model_response(),
            tool_call_id=part.tool_call_id,
            name=part.tool_name,
        )
    return ChatCompletionMessage(role="user", content=part.model_response())


def _from_response(message: ModelResponse) -> ChatCompletionMessage:
    """把一条模型回复折成网关的一条 role=assistant。

    pydantic-ai 把回复拆成多种 part：TextPart 是给用户看的正文，
    ThinkingPart 是思考链，ToolCallPart 是要执行的函数。Chat Completions
    没有「一条回复拆成多条 message」的写法，只能塞进同一条 assistant：正文进
    content，思考进 reasoning_content，函数调用进 tool_calls。
    不认识的 part 直接报错，避免历史被悄悄丢掉、下一轮对不齐。
    """
    texts: list[str] = []
    thinking: list[str] = []
    tool_calls: list[ChatMessageToolCall] = []
    for part in message.parts:
        if isinstance(part, TextPart):
            texts.append(part.content)
        elif isinstance(part, ThinkingPart):
            thinking.append(part.content)
        elif isinstance(part, ToolCallPart):
            tool_calls.append(
                ChatMessageToolCall(
                    tool_call_id=part.tool_call_id,
                    function=FunctionCall(
                        name=part.tool_name,
                        arguments=part.args_as_json_str(),
                    ),
                )
            )
        else:
            raise TypeError(f"unsupported model response part: {type(part).__name__}")
    return ChatCompletionMessage(
        role="assistant",
        content="".join(texts) or None,
        tool_calls=tool_calls or None,
        reasoning_content="".join(thinking) or None,
    )


def _text(content: object) -> str:
    return content if isinstance(content, str) else str(content)
