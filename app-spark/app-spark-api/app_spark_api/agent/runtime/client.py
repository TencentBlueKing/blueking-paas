# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Speaking the Agent Runtime's HTTP contract.

This layer is deliberately separate from provisioning. Where a Runtime lives is the provider's
business and will change -- local process today, remote sandbox later -- but a Runtime always
answers the same HTTP API, so nothing here needs to know which provider produced the URL.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx2

from app_spark_api.agent.runtime.entities import EventPage, RuntimeHealth
from app_spark_api.agent.runtime.exceptions import AgentBusyError, AgentUnavailableError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle

# What the AG-UI protocol asks for when it wants the event stream rather than a buffered body.
SSE_HEADERS = {"Accept": "text/event-stream", "Content-Type": "application/json"}

# A run waits on a model that may be writing files for minutes, so it gets no read timeout at
# all; `/health` and the drains are local cursor reads and should fail fast instead of hanging
# a view.
DEFAULT_TIMEOUT_SECONDS = 10.0

# Restoring a context is the exception: the body is the whole conversation, which can run to
# several megabytes, and it is written and fsynced on arrival. Kept in step with the agent's own
# CONTROL_PLANE_TIMEOUT_SECONDS, which is what it allows for the same document in the other
# direction. Too short here reports a cold start as unreachable while the Runtime is in fact
# rebasing successfully -- and the run then fails against a Runtime that just took the context.
CONTEXT_TIMEOUT_SECONDS = 30.0


class AgentRun:
    """One accepted run, whose AG-UI event stream is still open.

    Handing back an object rather than a bare generator is what makes a refused run reportable.
    An async generator runs no code until it is first iterated, and by then the view has already
    committed a status line -- so acceptance has to be settled in :meth:`AgentRuntimeClient.
    start_run` instead, and this only carries the bytes that follow.
    """

    def __init__(self, run_id: str, client: httpx2.AsyncClient, response: httpx2.Response) -> None:
        self.run_id = run_id
        self._client = client
        self._response = response

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        """Yield the SSE stream exactly as the Runtime wrote it.

        Forwarded raw rather than parsed and re-encoded: the events are AG-UI's, addressed to
        the browser, and this service has no business understanding them. Re-serializing every
        token delta would also cost a parse per event for nothing.
        """
        try:
            async for chunk in self._response.aiter_raw():
                yield chunk
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """Release the connection. Safe to call more than once."""
        await self._response.aclose()
        await self._client.aclose()


class AgentRuntimeClient:
    """An HTTP client for one conversation's Agent Runtime.

    Example::

        client = AgentRuntimeClient(handle)
        health = await client.health()
        run = await client.start_run(content="Create index.html", context_version=health.context_version)
        async for chunk in run.aiter_bytes():
            ...

    :param handle: Where the Runtime is reachable, as its provider reported it.
    :param timeout_seconds: Timeout for the small non-streaming calls.
    :param context_timeout_seconds: Timeout for the context restore, which carries a document
        the other calls do not.
    :param transport: What to send the requests over, defaulting to httpx's own. This is
        httpx's designated seam for replacing the network underneath a client; tests use it to
        stage the malformed answers a healthy Runtime cannot be asked to produce.
    """

    def __init__(
        self,
        handle: AgentRuntimeHandle,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        context_timeout_seconds: float = CONTEXT_TIMEOUT_SECONDS,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self.handle = handle
        self._timeout_seconds = timeout_seconds
        self._context_timeout_seconds = context_timeout_seconds
        self._transport = transport

    def _new_http_client(self, timeout: httpx2.Timeout | float) -> httpx2.AsyncClient:
        """Build a client for one exchange with the Runtime."""
        return httpx2.AsyncClient(
            base_url=self.handle.base_url,
            timeout=timeout,
            transport=self._transport,
            headers={"Authorization": f"Bearer {self.handle.runtime_token}"},
        )

    async def health(self) -> RuntimeHealth:
        """Read the Runtime's identity and the cursor of each durable channel.

        :return: The current snapshot.
        :raises AgentUnavailableError: If the Runtime cannot be reached or answers oddly.
        """
        return RuntimeHealth.from_payload(await self._get_json("/health"))

    async def read_ui_events(self, *, since: int = 0, limit: int | None = None) -> EventPage:
        """Read one page of the AG-UI event history.

        This is how a client that lost its stream catches up: SSE has no replay of its own, so
        the events it missed can only come from the Runtime's own log.

        :param since: Cursor to resume from; ``0`` starts at the beginning.
        :param limit: Page size, left to the Runtime's default when omitted.
        :return: One page, plus the cursor needed to ask for the next.
        :raises AgentUnavailableError: If the Runtime cannot be reached or answers oddly.
        """
        params: dict[str, int] = {"since": since}
        if limit is not None:
            params["limit"] = limit
        return EventPage.from_payload(await self._get_json("/ui-events", params=params))

    async def restore_context(
        self,
        document: dict[str, Any],
        *,
        if_match: int,
        log_seq: int,
        ui_event_seq: int,
    ) -> int:
        """Seed an empty Runtime with an archived conversation, and with where it left off.

        This is the cold start. The document is forwarded byte for byte as it was archived --
        it is the Runtime's own export format and this service does not interpret it -- while
        the two cursors ride as query parameters, which is what keeps the body identical to
        what a ``GET /context`` produced.

        The cursors matter as much as the document. Without them the new Runtime would number
        its first entry 1, colliding with the entry 1 this service already holds for the same
        conversation, and there would be no way to tell the two apart afterwards.

        :param document: Archived context, as ``ConversationContext.as_payload`` produced it.
        :param if_match: Context version the Runtime is expected to be at, normally ``0``. A
            Runtime that has moved on refuses rather than losing a conversation of its own.
        :param log_seq: Last transcript sequence number this service holds.
        :param ui_event_seq: Last AG-UI event sequence number this service holds.
        :return: The context version the Runtime now serves.
        :raises AgentBusyError: If a run is occupying the Runtime.
        :raises AgentUnavailableError: If the Runtime cannot be reached or refuses the restore.
        """
        params = {"log_seq": log_seq, "ui_event_seq": ui_event_seq}
        try:
            async with self._new_http_client(self._context_timeout_seconds) as client:
                response = await client.put(
                    "/context",
                    params=params,
                    headers={"If-Match": str(if_match)},
                    json=document,
                )
        except httpx2.HTTPError as exc:
            raise AgentUnavailableError(f"Could not restore the context on the Agent Runtime: {exc}") from exc

        if response.status_code == HTTPStatus.CONFLICT:
            raise AgentBusyError(await self._read_error(response))
        if response.status_code != HTTPStatus.OK:
            detail = await self._read_error(response)
            raise AgentUnavailableError(f"The Agent Runtime refused the context with {response.status_code}: {detail}")
        return _restored_version(response)

    async def start_run(
        self,
        *,
        content: str,
        context_version: int,
        run_id: str | None = None,
    ) -> AgentRun:
        """Submit one conversation turn and return its still-open event stream.

        Only the new user message is sent. The Runtime owns the history and rejects anything a
        client tries to resend, so there is nothing here to keep in step with it.

        :param content: The user's message for this turn.
        :param context_version: Version read from ``/health`` immediately beforehand. Compaction
            can move it in the middle of a run, so a value carried over from an earlier turn is
            not good enough.
        :param run_id: Identifier for this turn; a fresh UUID when omitted. The Runtime refuses
            a replayed one.
        :return: The accepted run.
        :raises AgentBusyError: If a run is already occupying the Runtime.
        :raises AgentUnavailableError: If the Runtime cannot be reached or refuses the turn.
        """
        run_id = run_id or str(uuid4())
        body = {
            # AG-UI's own document, so it keeps AG-UI's camelCase -- `threadId` included, which
            # is the protocol's name for what everything else here calls a conversation.
            "threadId": self.handle.conversation_id,
            "runId": run_id,
            "state": {},
            "messages": [{"id": str(uuid4()), "role": "user", "content": content}],
            "tools": [],
            "context": [],
            "forwardedProps": {"contextVersion": context_version},
        }

        # No read timeout: the stream stays open for as long as the model keeps working.
        client = self._new_http_client(httpx2.Timeout(self._timeout_seconds, read=None))
        try:
            request = client.build_request("POST", "/runs", headers=SSE_HEADERS, json=body)
            response = await client.send(request, stream=True)
        except httpx2.HTTPError as exc:
            await client.aclose()
            raise AgentUnavailableError(f"Could not start a run on the Agent Runtime: {exc}") from exc
        except BaseException:
            await client.aclose()
            raise

        if response.status_code != HTTPStatus.OK:
            detail = await self._read_error(response)
            await response.aclose()
            await client.aclose()
            if response.status_code == HTTPStatus.CONFLICT:
                raise AgentBusyError(detail)
            raise AgentUnavailableError(f"The Agent Runtime refused the run with {response.status_code}: {detail}")

        return AgentRun(run_id, client, response)

    async def _get_json(self, path: str, *, params: dict[str, int] | None = None) -> Any:
        """Perform one buffered GET and return its decoded body."""
        try:
            async with self._new_http_client(self._timeout_seconds) as client:
                response = await client.get(path, params=params)
                if response.status_code != HTTPStatus.OK:
                    raise AgentUnavailableError(
                        f"The Agent Runtime answered {path} with {response.status_code}: {response.text[:200]}"
                    )
                return response.json()
        except httpx2.HTTPError as exc:
            raise AgentUnavailableError(f"Could not reach the Agent Runtime at {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AgentUnavailableError(f"The Agent Runtime answered {path} with non-JSON: {exc}") from exc

    @staticmethod
    async def _read_error(response: httpx2.Response) -> str:
        """Return the Runtime's explanation for a refusal, however it phrased it."""
        try:
            await response.aread()
        except httpx2.HTTPError as exc:  # pragma: no cover - only on a mid-refusal disconnect
            return f"the response body could not be read: {exc}"
        try:
            payload = response.json()
        except json.JSONDecodeError, UnicodeDecodeError:
            return response.text[:200]
        if isinstance(payload, dict) and "detail" in payload:
            return str(payload["detail"])
        return response.text[:200]


def _restored_version(response: httpx2.Response) -> int:
    """Read the context version out of a successful restore.

    Taken from the ``ETag`` the Runtime tags its context with, which is the same value the
    body carries -- and reading it from the header means not having to parse a document that
    can run to megabytes just to learn one integer.
    """
    try:
        return int(response.headers["ETag"])
    except (KeyError, ValueError) as exc:
        raise AgentUnavailableError(f"The Agent Runtime restored a context without a usable ETag: {exc}") from exc
