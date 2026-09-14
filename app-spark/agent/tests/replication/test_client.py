"""The control-plane error contract is independent of its server framework."""

from http import HTTPStatus

import httpx
import pytest

from app_spark_agent.replication.client import ControlPlaneClient, ControlPlaneError
from app_spark_agent.state import Channel


@pytest.mark.parametrize("operation", ["append", "put_context", "put_checkpoint"])
async def test_structured_api_errors_keep_the_code_detail_and_http_status(operation):
    def respond(request):
        return httpx.Response(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            json={"code": "INVALID_CONVERSATION_STATE", "detail": "The conversation state is invalid."},
        )

    client = ControlPlaneClient(
        base_url="http://api.invalid/state/", token="secret", transport=httpx.MockTransport(respond)
    )
    try:
        call = client.append(Channel.MESSAGE, []) if operation == "append" else getattr(client, operation)({})
        with pytest.raises(ControlPlaneError) as caught:
            await call
        error = caught.value
        assert error.status_code == 422
        assert error.code == "INVALID_CONVERSATION_STATE"
        assert error.detail == "The conversation state is invalid."
        assert "INVALID_CONVERSATION_STATE" in str(error)
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("body", "expected_detail"),
    [
        ({"detail": "legacy error"}, "legacy error"),
        ({"code": 42, "detail": ["invalid shape"]}, None),
        (["not an object"], None),
    ],
)
async def test_legacy_or_malformed_error_envelopes_preserve_http_status(body, expected_detail):
    client = ControlPlaneClient(
        base_url="http://api.invalid/state/",
        token="secret",
        transport=httpx.MockTransport(lambda request: httpx.Response(403, json=body)),
    )
    try:
        with pytest.raises(ControlPlaneError) as caught:
            await client.put_context({})
        assert caught.value.status_code == 403
        assert caught.value.code is None
        assert caught.value.detail == expected_detail
    finally:
        await client.aclose()


async def test_proxy_error_pages_are_not_copied_into_exceptions():
    client = ControlPlaneClient(
        base_url="http://api.invalid/state/",
        token="secret",
        transport=httpx.MockTransport(lambda request: httpx.Response(502, text="<html>private-proxy-dump</html>")),
    )
    try:
        with pytest.raises(ControlPlaneError) as caught:
            await client.put_context({})
        assert caught.value.status_code == 502
        assert caught.value.code is None
        assert caught.value.detail is None
        assert "private-proxy-dump" not in str(caught.value)
    finally:
        await client.aclose()


async def test_transport_failures_do_not_invent_a_server_error_code():
    def respond(request):
        raise httpx.ConnectError("unreachable")

    client = ControlPlaneClient(
        base_url="http://api.invalid/state/", token="secret", transport=httpx.MockTransport(respond)
    )
    try:
        with pytest.raises(ControlPlaneError) as caught:
            await client.put_context({})
        assert caught.value.status_code is None
        assert caught.value.code is None
    finally:
        await client.aclose()
