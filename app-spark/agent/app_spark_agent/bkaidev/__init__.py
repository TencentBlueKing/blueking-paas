"""bkaidev LLM 网关：鉴权、类型化客户端、挂在已有持久化上的对话中间层。"""

from app_spark_agent.bkaidev.auth import (
    BKAPI_AUTHORIZATION_HEADER,
    OPENAI_API_KEY_PLACEHOLDER,
    authorization_headers,
    authorization_payload,
)
from app_spark_agent.bkaidev.client import AidevApiClient, AidevApiError
from app_spark_agent.bkaidev.session import ConversationSession, SessionCursors
from app_spark_agent.bkaidev.types import (
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    FunctionTool,
    ModelList,
)

__all__ = [
    "BKAPI_AUTHORIZATION_HEADER",
    "OPENAI_API_KEY_PLACEHOLDER",
    "AidevApiClient",
    "AidevApiError",
    "ChatCompletionMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ConversationSession",
    "FunctionTool",
    "ModelList",
    "SessionCursors",
    "authorization_headers",
    "authorization_payload",
]
