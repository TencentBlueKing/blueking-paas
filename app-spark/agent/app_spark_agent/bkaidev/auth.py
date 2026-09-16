"""bkaidev 网关鉴权：只允许用户态 access_token。

对话协议与 OpenAI 兼容客户端共用；鉴权不能共用。bkaidev 走
X-Bkapi-Authorization（JSON 字符串），不是 Authorization: Bearer。

空间和智能体由 app-spark 在接入层创建，本组件只消费注入的 token。
禁止把 bk_app_code / bk_app_secret 写进请求头或交给模型。
"""

import json

import httpx2

# 蓝鲸网关公共鉴权头。值为 JSON 字符串，本期只放 access_token。
BKAPI_AUTHORIZATION_HEADER = "X-Bkapi-Authorization"

# bkaidev 自己的 OpenAI 客户端把 api_key 填成这个占位；真正过网关靠上面那个头。
OPENAI_API_KEY_PLACEHOLDER = "empty"


def authorization_payload(access_token: str) -> dict[str, str]:
    """构造 X-Bkapi-Authorization 的 JSON 对象，只含 access_token。

    :param access_token: 注入到沙箱的用户态 token。
    :raises ValueError: token 为空。
    """
    token = access_token.strip()
    if not token:
        raise ValueError("access_token is required")
    return {"access_token": token}


def authorization_headers(access_token: str) -> dict[str, str]:
    """返回出站 HTTP 头。JSON 用紧凑分隔符，避免空白差异干扰对照。"""
    return {
        BKAPI_AUTHORIZATION_HEADER: json.dumps(
            authorization_payload(access_token),
            separators=(",", ":"),
        )
    }


class WithoutAuthorization(httpx2.AsyncBaseTransport):
    """剥掉 OpenAI SDK 自动加上的 Authorization: Bearer <api_key>。

    api_key 必须填占位才能构造客户端，但出站只允许 X-Bkapi-Authorization。
    锁定的 openai v3.x 依赖 httpx2；AidevApiClient 用的是 httpx，两个包不能通用。
    """

    def __init__(self, wrapped: httpx2.AsyncBaseTransport | None = None) -> None:
        self._wrapped = wrapped or httpx2.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        headers = httpx2.Headers(request.headers)
        headers.pop("Authorization", None)
        request.headers = headers
        return await self._wrapped.handle_async_request(request)
