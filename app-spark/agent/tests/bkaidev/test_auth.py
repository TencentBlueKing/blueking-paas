"""出站鉴权头只允许 access_token，不能夹带应用凭证。"""

import json

import httpx2
import pytest

from app_spark_agent.bkaidev.auth import (
    BKAPI_AUTHORIZATION_HEADER,
    WithoutAuthorization,
    authorization_headers,
    authorization_payload,
)


def test_authorization_payload_contains_only_access_token() -> None:
    payload = authorization_payload("  user-token  ")

    assert payload == {"access_token": "user-token"}
    assert set(payload) == {"access_token"}


def test_authorization_header_is_compact_json() -> None:
    headers = authorization_headers("user-token")

    assert headers == {BKAPI_AUTHORIZATION_HEADER: '{"access_token":"user-token"}'}
    parsed = json.loads(headers[BKAPI_AUTHORIZATION_HEADER])
    assert "bk_app_code" not in parsed
    assert "bk_app_secret" not in parsed


@pytest.mark.parametrize("token", ["", "   "])
def test_empty_access_token_is_rejected(token: str) -> None:
    with pytest.raises(ValueError, match="access_token"):
        authorization_payload(token)


async def test_without_authorization_strips_bearer() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.update({key.lower(): value for key, value in request.headers.items()})
        return httpx2.Response(200, json={"ok": True})

    transport = WithoutAuthorization(httpx2.MockTransport(handler))
    async with httpx2.AsyncClient(transport=transport) as client:
        await client.get("https://gw.test/v1/models", headers={"Authorization": "Bearer empty"})

    assert "authorization" not in seen
