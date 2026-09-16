"""可信历史到 OpenAI messages 的映射，含工具调用。"""

import pytest
from pydantic_ai.messages import (
    InstructionPart,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from app_spark_agent.bkaidev.messages import openai_messages_from_model_messages


def test_request_and_response_parts_map_to_openai_roles() -> None:
    messages = openai_messages_from_model_messages(
        [
            ModelRequest(parts=[SystemPromptPart(content="sys"), UserPromptPart(content="hi")]),
            ModelResponse(
                parts=[
                    TextPart(content="call it"),
                    ToolCallPart(tool_name="read_file", args={"path": "a.py"}, tool_call_id="call_1"),
                ],
                model_name="deepseek-v4-flash",
            ),
            ModelRequest(parts=[ToolReturnPart(tool_name="read_file", content="print(1)", tool_call_id="call_1")]),
        ]
    )

    assert [item.role for item in messages] == ["system", "user", "assistant", "tool"]
    assert messages[2].tool_calls is not None
    assert messages[2].tool_calls[0].tool_call_id == "call_1"
    assert messages[2].tool_calls[0].function.name == "read_file"
    assert messages[2].tool_calls[0].model_dump(by_alias=True)["id"] == "call_1"
    assert messages[2].tool_calls[0].model_dump(by_alias=True)["type"] == "function"
    assert messages[3].tool_call_id == "call_1"
    assert messages[3].content == "print(1)"


def test_retry_prompt_pairs_with_the_tool_call() -> None:
    messages = openai_messages_from_model_messages(
        [
            ModelResponse(
                parts=[ToolCallPart(tool_name="read_file", args={"path": "a.py"}, tool_call_id="call_1")],
                model_name="deepseek-v4-flash",
            ),
            ModelRequest(
                parts=[
                    RetryPromptPart(
                        content="path is required",
                        tool_name="read_file",
                        tool_call_id="call_1",
                    )
                ]
            ),
        ]
    )

    assert [item.role for item in messages] == ["assistant", "tool"]
    assert messages[1].tool_call_id == "call_1"
    assert messages[1].name == "read_file"
    assert messages[1].content is not None
    assert "path is required" in messages[1].content


def test_unknown_request_parts_are_rejected() -> None:
    with pytest.raises(TypeError, match="unsupported model request part"):
        openai_messages_from_model_messages([ModelRequest(parts=[InstructionPart(content="skill")])])
