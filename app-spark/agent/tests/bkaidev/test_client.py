"""AidevApiClient 打到正确的 OpenAPI 路径，并带上 access_token 头。"""

import json

import httpx
import pytest

from app_spark_agent.bkaidev.auth import BKAPI_AUTHORIZATION_HEADER
from app_spark_agent.bkaidev.client import AidevApiClient, AidevApiError
from app_spark_agent.bkaidev.types import ChatCompletionMessage, ChatCompletionRequest


def _router(request: httpx.Request) -> httpx.Response:
    auth = json.loads(request.headers[BKAPI_AUTHORIZATION_HEADER])
    assert auth == {"access_token": "user-token"}
    assert "authorization" not in {key.lower() for key in request.headers}
    assert "bk_app_secret" not in auth

    if request.method == "GET" and request.url.path.endswith("/models"):
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {
                        "id": "deepseek-v4-flash",
                        "object": "model",
                        "created": 1,
                        "owned_by": "aidev",
                    }
                ],
            },
        )
    if request.method == "POST" and request.url.path.endswith("/chat/completions"):
        body = json.loads(request.content)
        assert body["model"] == "deepseek-v4-flash"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 1,
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )
    if request.url.path.endswith("/denied"):
        return httpx.Response(403, json={"error": {"message": "该应用无访问该模型的权限", "code": 40301}})
    return httpx.Response(404, text="missing")


@pytest.fixture
def client() -> AidevApiClient:
    return AidevApiClient(
        base_url="https://bkaidev.test/prod/openapi/aidev/gateway/llm/v1",
        access_token="user-token",
        transport=httpx.MockTransport(_router),
    )


async def test_list_models_uses_openai_compatible_path(client: AidevApiClient) -> None:
    listed = await client.list_models()

    assert [card.llm_code for card in listed.data] == ["deepseek-v4-flash"]
    assert listed.object_type == "list"
    assert listed.data[0].model_dump(by_alias=True)["id"] == "deepseek-v4-flash"


async def test_create_chat_completion_round_trips(client: AidevApiClient) -> None:
    response = await client.create_chat_completion(
        ChatCompletionRequest(
            model="deepseek-v4-flash",
            messages=[ChatCompletionMessage(role="user", content="hello")],
        )
    )

    assert response.choices[0].message.content == "ok"
    assert response.choices[0].finish_reason == "stop"


async def test_gateway_error_is_typed() -> None:
    async def deny(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "该应用无访问该模型的权限", "code": 40301}})

    client = AidevApiClient(
        base_url="https://bkaidev.test/v1",
        access_token="user-token",
        transport=httpx.MockTransport(deny),
    )

    with pytest.raises(AidevApiError, match="该应用无访问该模型的权限") as exc_info:
        await client.list_models()

    assert exc_info.value.status_code == 403
    assert "user-token" not in str(exc_info.value)
