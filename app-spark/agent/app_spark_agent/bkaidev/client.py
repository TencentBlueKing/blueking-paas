"""bkaidev LLM 网关的类型化 HTTP 客户端。

只调本期需要的两条 OpenAPI 资源：GET {BASE_URL}/models，以及
POST {BASE_URL}/chat/completions。鉴权只用用户态 access_token。
空间 / 智能体的创建不在本组件。
"""

from typing import Self

import httpx
from pydantic import ValidationError

from app_spark_agent import settings
from app_spark_agent.bkaidev.auth import authorization_headers
from app_spark_agent.bkaidev.types import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
    ModelList,
)


class AidevApiError(RuntimeError):
    """网关返回了非 2xx。status_code 留给调用方区分 4xx / 5xx。"""

    def __init__(self, status_code: int, message: str, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"bkaidev gateway {status_code}: {message}")


class AidevApiClient:
    """对 MODEL_BASE_URL 指向的 LLM 网关发 OpenAI 兼容请求。

    :param base_url: v1 层地址，不要带 /chat/completions。
    :param access_token: 用户态 token，只进 X-Bkapi-Authorization。
    :param timeout: 单次请求超时秒数。
    :param transport: 测试注入的 httpx transport。
    """

    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=authorization_headers(access_token),
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_settings(cls) -> "AidevApiClient":
        """用当前进程注入的 token 和网关地址构造客户端。"""
        token = settings.gateway_access_token()
        if token is None:
            raise ValueError("BK_AIDEV_ACCESS_TOKEN or MODEL_API_KEY is required")

        base_url = settings.MODEL_BASE_URL.strip()
        if not base_url:
            raise ValueError("MODEL_BASE_URL is required")

        return cls(base_url=base_url, access_token=token)

    async def aclose(self) -> None:
        """关闭底层 HTTP 连接池。"""
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def list_models(self) -> ModelList:
        """GET /models：当前 access_token 能用的 llm_code 列表。"""
        response = await self._client.get("/models")
        return ModelList.model_validate(self._json(response))

    async def create_chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """POST /chat/completions：一次非流式对话。"""
        payload = request.model_dump(mode="json", exclude_none=True, by_alias=True)
        response = await self._client.post("/chat/completions", json=payload)
        return ChatCompletionResponse.model_validate(self._json(response))

    def _json(self, response: httpx.Response) -> object:
        """把响应校验成 JSON；非 2xx 抽错误信息，正文不含鉴权头。"""
        if response.is_success:
            return response.json()

        try:
            parsed = ErrorResponse.model_validate_json(response.text)
        except ValidationError, ValueError:
            message = response.text or response.reason_phrase
        else:
            message = parsed.error.message
        raise AidevApiError(response.status_code, message, body=response.text)
