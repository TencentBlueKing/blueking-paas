"""bkaidev LLM 网关鉴权。"""

from app_spark_agent.bkaidev.auth import (
    BKAPI_AUTHORIZATION_HEADER,
    OPENAI_API_KEY_PLACEHOLDER,
    authorization_headers,
    authorization_payload,
)

__all__ = [
    "BKAPI_AUTHORIZATION_HEADER",
    "OPENAI_API_KEY_PLACEHOLDER",
    "authorization_headers",
    "authorization_payload",
]
