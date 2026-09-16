"""对话中间层从 context.json 取历史，不从 log.jsonl 拼消息。"""

import json
from uuid import uuid4

import httpx
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from app_spark_agent.bkaidev.client import AidevApiClient
from app_spark_agent.bkaidev.session import ConversationSession
from app_spark_agent.bkaidev.types import ChatCompletionMessage
from app_spark_agent.state import AppendLog, ContextStore, ConversationContext


def _stores(tmp_path):
    context_store = ContextStore(tmp_path / "context.json")
    transcript = AppendLog(tmp_path / "log.jsonl", payload_key="message")
    ui_events = AppendLog(tmp_path / "ui_events.jsonl", payload_key="event")
    return context_store, transcript, ui_events


async def test_history_comes_from_context_not_transcript(tmp_path) -> None:
    conversation_id = str(uuid4())
    context_store, transcript, ui_events = _stores(tmp_path)
    await context_store.restore(
        ConversationContext(
            conversation_id=conversation_id,
            context_version=1,
            messages=[
                ModelRequest(parts=[UserPromptPart(content="hello")], conversation_id=conversation_id),
                ModelResponse(
                    parts=[TextPart(content="world")],
                    model_name="deepseek-v4-flash",
                    conversation_id=conversation_id,
                ),
            ],
        )
    )
    await transcript.append("run-1", [{"kind": "raw-transcript-must-not-be-sent"}])
    await ui_events.append("run-1", [{"type": "TEXT_MESSAGE_CONTENT"}])

    session = ConversationSession(
        client=AidevApiClient(
            base_url="https://bkaidev.test/v1",
            access_token="user-token",
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),
        ),
        context_store=context_store,
        transcript=transcript,
        ui_events=ui_events,
    )

    history = session.history()
    cursors = session.cursors

    assert [message.role for message in history] == ["user", "assistant"]
    assert [message.content for message in history] == ["hello", "world"]
    assert cursors.conversation_id == conversation_id
    assert cursors.context_version == 1
    assert cursors.log_seq == 1
    assert cursors.ui_event_seq == 1


async def test_create_completion_sends_context_plus_extra(tmp_path) -> None:
    conversation_id = str(uuid4())
    context_store, transcript, ui_events = _stores(tmp_path)
    await context_store.restore(
        ConversationContext(
            conversation_id=conversation_id,
            context_version=2,
            messages=[
                ModelRequest(parts=[UserPromptPart(content="prior")], conversation_id=conversation_id),
            ],
        )
    )
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-2",
                "object": "chat.completion",
                "created": 1,
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "next"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    session = ConversationSession(
        client=AidevApiClient(
            base_url="https://bkaidev.test/v1",
            access_token="user-token",
            transport=httpx.MockTransport(handler),
        ),
        context_store=context_store,
        transcript=transcript,
        ui_events=ui_events,
    )

    response = await session.create_completion(
        [ChatCompletionMessage(role="user", content="now")],
        model="deepseek-v4-flash",
    )

    body = seen["body"]
    assert isinstance(body, dict)
    assert [item["content"] for item in body["messages"]] == ["prior", "now"]
    assert response.choices[0].message.content == "next"
    assert session.context.context_version == 2
    assert transcript.last_seq == 0
    assert (tmp_path / "context.json").exists()
    assert not (tmp_path / "log.jsonl").exists()
