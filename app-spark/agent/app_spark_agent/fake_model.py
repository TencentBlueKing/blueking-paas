"""不依赖真实 LLM 的确定性模型，让 Runtime 可以被零成本地真正启动。

不直接用 pydantic-ai 自带的 ``TestModel``（``MODEL=test`` 就能启用）的原因是：它会拿编造的
参数去调用**所有**可用工具，包括 Shell，行为既不确定也读不懂。这里要的是一段演得像 LLM 的
确定性脚本。

三个场景：

- ``write-file``（默认）：先调 ``write_file`` 落一个文件，拿到工具结果后再流式回一段说明。
  一轮里就覆盖了工具调用 delta、工具结果、一轮内多次模型请求，以及 workspace 真实变更。
- ``chat``：只流式回文本，用于最朴素的「SSE 通不通」断言。
- ``slow``：先吐一个 chunk 让流真的开始，再挂起 ``FAKE_DELAY_SECONDS``。调用方因此可以在
  run 确实在飞的时候发第二个请求，去验证 Runtime 的 409——不靠 sleep 猜时序。

用法::

    APP_SPARK_AGENT_MODEL=fake:write-file uv run uvicorn app_spark_agent.server.asgi:app

已知边界：``SummarizingCompaction`` 没有自己的模型时会借用本轮的模型，届时这段脚本会去写
文件而不是总结。触发点在 ``COMPACTION_TARGET_TOKENS``（默认 48 万 token），假模型的使用场景
够不到，因此不做处理。
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel

from app_spark_agent import settings

# ``infer_model`` 只认 ``provider:model``，未知 provider 会直接抛 UserError，所以这个前缀
# 必须在 `build_model()` 里被提前拦下来，不能指望 pydantic-ai 分发。
FAKE_MODEL_PREFIX = "fake:"

# harness ``FileSystem`` 能力暴露的写文件工具，签名是 ``write_file(path, content)``。
WRITE_FILE_TOOL = "write_file"

SCENARIO_WRITE_FILE = "write-file"
SCENARIO_CHAT = "chat"
SCENARIO_SLOW = "slow"

DEFAULT_SCENARIO = SCENARIO_WRITE_FILE
SCENARIOS = (SCENARIO_WRITE_FILE, SCENARIO_CHAT, SCENARIO_SLOW)

# 假模型每轮写的文件名。带上轮次，连续多轮就会留下可区分、可断言的产物。
NOTE_FILENAME_TEMPLATE = "fake-agent-note-{turn}.md"

# 文本按「词 + 其后空白」切块。一次性吐完的假模型会让 delta 通路的 bug 悄悄溜过去。
_CHUNK_RE = re.compile(r"\S+\s*")


class UnknownFakeScenarioError(ValueError):
    """``APP_SPARK_AGENT_MODEL`` 指定了一个不存在的假场景。"""


@dataclass(frozen=True)
class ToolCallStep:
    """本次模型请求要发起的一次工具调用。"""

    tool_name: str
    args: dict[str, object]
    tool_call_id: str


@dataclass(frozen=True)
class TextStep:
    """本次模型请求要流式吐出的文本。

    :param chunks: 依次吐出的文本块。
    :param pause_after: 在第几块之后挂起 ``FAKE_DELAY_SECONDS``；``None`` 表示不挂起。
    """

    chunks: tuple[str, ...]
    pause_after: int | None = field(default=None)


Step = ToolCallStep | TextStep


def build_fake_model(scenario: str) -> Model:
    """构造 ``fake:`` 前缀指定的假模型。

    :param scenario: ``fake:`` 之后的部分，空串表示使用默认场景。
    :return: 一个不发起任何网络请求的确定性模型。
    :raises UnknownFakeScenarioError: 场景名不在 :data:`SCENARIOS` 里。
    """
    name = scenario or DEFAULT_SCENARIO
    if name not in SCENARIOS:
        supported = ", ".join(SCENARIOS)
        raise UnknownFakeScenarioError(f"Unknown fake model scenario: {name!r}. Supported scenarios: {supported}.")

    async def stream(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> AsyncIterator[str | DeltaToolCalls]:
        step = plan_step(name, messages)
        if isinstance(step, ToolCallStep):
            # 一次流式响应里不能混着吐文本和工具调用，所以「写文件」和「说明写了什么」
            # 天然就是两次模型请求——这也正是真实 Agent 循环的样子。
            yield {
                0: DeltaToolCall(
                    name=step.tool_name,
                    json_args=json.dumps(step.args),
                    tool_call_id=step.tool_call_id,
                )
            }
            return
        for index, chunk in enumerate(step.chunks):
            yield chunk
            if step.pause_after is not None and index == step.pause_after:
                await asyncio.sleep(settings.FAKE_DELAY_SECONDS)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        # 非流式入口。正常 run 全走 stream，但压缩之类的内部调用可能落到这里，给它一个
        # 说得通的答复，好过让 FunctionModel 抛「必须提供 function」。
        step = plan_step(name, messages)
        if isinstance(step, ToolCallStep):
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name=step.tool_name,
                        args=step.args,
                        tool_call_id=step.tool_call_id,
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="".join(step.chunks))])

    return FunctionModel(respond, stream_function=stream, model_name=f"{FAKE_MODEL_PREFIX}{name}")


def plan_step(scenario: str, messages: Sequence[ModelMessage]) -> Step:
    """决定这一次模型请求该做什么。

    状态一律从 ``messages`` 推导，不用闭包计数器：一个进程要服务很多轮对话，计数器会让第二
    轮行为错乱，而压缩会在一轮中间改写历史，把任何攒在外面的状态也一并弄脏。

    :param scenario: 已校验过的场景名。
    :param messages: 本次请求的完整历史。
    :return: 本次请求要执行的动作。
    """
    prompt = last_user_prompt(messages)
    if scenario == SCENARIO_CHAT:
        return TextStep(chunks=chunks(f"You said: {prompt}"))
    if scenario == SCENARIO_SLOW:
        # 挂在第一块之后：调用方能先收到流真的开始了，再放心地去触发并发请求。
        return TextStep(chunks=chunks(f"Thinking about: {prompt}"), pause_after=0)

    turn = count_user_prompts(messages)
    filename = NOTE_FILENAME_TEMPLATE.format(turn=turn)
    if wrote_file_this_run(messages):
        return TextStep(chunks=chunks(f"Done. I wrote your request into {filename}."))
    return ToolCallStep(
        tool_name=WRITE_FILE_TOOL,
        args={"path": filename, "content": f"# Turn {turn}\n\n{prompt}\n"},
        tool_call_id=f"fake-write-file-{turn}",
    )


def wrote_file_this_run(messages: Sequence[ModelMessage]) -> bool:
    """本轮（最后一条用户消息之后）是否已经写过文件。

    只看最后一条用户消息之后的部分，而不是整段历史：上一轮留下的工具结果还在历史里，按整段
    历史判断会让第二轮直接跳过写文件。
    """
    for message in reversed(messages):
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    # 倒着走到了本轮的用户消息，说明其后没有出现过写文件的结果。
                    return False
                if isinstance(part, ToolReturnPart) and part.tool_name == WRITE_FILE_TOOL:
                    return True
    return False


def count_user_prompts(messages: Sequence[ModelMessage]) -> int:
    """返回历史里用户消息的条数，也就是当前是第几轮。"""
    return sum(
        1
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart)
    )


def last_user_prompt(messages: Sequence[ModelMessage]) -> str:
    """返回最后一条用户消息的文本，没有则返回空串。

    多模态输入的 ``content`` 不是字符串，假模型只需要一个能回显的摘要，因此原样 ``str()``。
    """
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        for part in reversed(message.parts):
            if isinstance(part, UserPromptPart):
                return part.content if isinstance(part.content, str) else str(part.content)
    return ""


def chunks(text: str) -> tuple[str, ...]:
    """把一段文本切成多块，好让流式通路真的被走到。"""
    return tuple(_CHUNK_RE.findall(text)) or (text,)
