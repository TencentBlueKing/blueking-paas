"""Speaking the control plane's state-ingest contract.

The Runtime knows nothing about conversations, projects, or tenants on the other side. It is
handed one already conversation-scoped base URL and one token, and it appends to the channels
underneath that URL. Everything the control plane needs to route a write is therefore already
in the address it chose to hand out, which is what keeps this module free of any notion of
identity.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any, cast

import httpx

from app_spark_agent.state import Channel

# How long a single ingest call may take. Generous because a context document can be several
# megabytes, but finite: a control plane that has stopped answering must not pin the
# replicator's task forever, since a run's end-of-turn flush waits on it.
DEFAULT_TIMEOUT_SECONDS = 30.0

# The path each channel is appended to, relative to the conversation-scoped base URL. Kept as a
# table rather than derived from the enum value, because the wire spelling is the control
# plane's REST convention (`ui-events`) and the channel name is ours (`ui_event`).
_CHANNEL_PATHS = {
    Channel.MESSAGE: "messages",
    Channel.UI_EVENT: "ui-events",
}

CONTEXT_PATH = "context"


class ControlPlaneError(RuntimeError):
    """Raised when the control plane cannot be reached or refused a write."""


class ControlPlaneClient:
    """An HTTP client for one conversation's state-ingest endpoints.

    Example::

        client = ControlPlaneClient(
            base_url="http://api/api/internal/conversations/<uuid>/state/",
            token="...",
        )
        acknowledged = await client.append(Channel.MESSAGE, records)

    :param base_url: Conversation-scoped root the ingest endpoints hang off.
    :param token: Bearer token minted by the control plane when it started this Runtime.
    :param timeout_seconds: Timeout for a single ingest call.
    :param transport: What to send requests over, defaulting to httpx's own. This is httpx's
        designated seam for replacing the network underneath a client; tests use it to drive a
        real ingest application in-process instead of over a socket.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # A trailing slash so `httpx` resolves the relative channel paths *under* the base
        # rather than replacing its last segment.
        self.base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def append(self, channel: Channel, records: Sequence[dict[str, Any]]) -> int:
        """Hand one batch of channel entries to the control plane.

        Safe to repeat: entries are identified by their sequence number, so a batch that was
        accepted but whose acknowledgement was lost is ignored the second time round.

        :param channel: Channel the entries belong to.
        :param records: Entries as :meth:`~app_spark_agent.state.log.AppendLog.dump` produced
            them.
        :return: The last sequence number the control plane now holds for this channel, which
            may be ahead of this batch if an earlier retry already landed.
        :raises ControlPlaneError: If the control plane cannot be reached or refused the batch.
        """
        payload = await self._send("POST", _CHANNEL_PATHS[channel], {"records": list(records)})
        return _read_int(payload, "last_seq")

    async def put_context(self, context: dict[str, Any]) -> int:
        """Replace the control plane's copy of the conversation context.

        Not an append: only the newest version means anything, so a version the control plane
        has already moved past is expected to be accepted as a no-op rather than refused.

        :param context: Context document as ``ConversationContext.as_payload`` produced it.
        :return: The context version the control plane now holds.
        :raises ControlPlaneError: If the control plane cannot be reached or refused the write.
        """
        payload = await self._send("PUT", CONTEXT_PATH, context)
        return _read_int(payload, "context_version")

    async def aclose(self) -> None:
        """Release the underlying connection pool."""
        await self._client.aclose()

    async def _send(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Perform one ingest call and return its decoded body."""
        try:
            response = await self._client.request(method, path, json=body)
        except httpx.HTTPError as exc:
            raise ControlPlaneError(f"could not reach the control plane at {path}: {exc}") from exc

        if response.status_code != HTTPStatus.OK:
            raise ControlPlaneError(
                f"the control plane answered {path} with {response.status_code}: {response.text[:200]}"
            )
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ControlPlaneError(f"the control plane answered {path} with non-JSON") from exc
        if not isinstance(payload, dict):
            raise ControlPlaneError(f"expected a JSON object from {path}, got {payload!r}")
        # `Response.json()` is `Any`, so narrowing it to a dict leaves the key and value types
        # unknown; this is the one place that names them.
        return cast(dict[str, Any], payload)


def _read_int(payload: dict[str, Any], key: str) -> int:
    """Return one integer field of an ingest response, or say what was wrong with it."""
    try:
        return int(payload[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ControlPlaneError(f"unreadable ingest response, {key} is missing or not an integer: {exc}") from exc
