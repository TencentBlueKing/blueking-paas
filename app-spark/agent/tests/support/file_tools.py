"""Drive the harness file tools the way the model does."""

import asyncio
import json
from collections.abc import AsyncIterator

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel


def read_file_result(agent: Agent[None, str], path: str) -> str:
    """Return what read_file answers the model for path, through a real run of agent."""
    issued = False

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str | DeltaToolCalls]:
        nonlocal issued
        if issued:
            yield "done"
            return
        issued = True
        yield {0: DeltaToolCall(name="read_file", json_args=json.dumps({"path": path}), tool_call_id="read-1")}

    result = asyncio.run(agent.run("read", model=FunctionModel(stream_function=stream)))
    return next(
        str(part.content)
        for message in result.all_messages()
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_call_id == "read-1"
    )
