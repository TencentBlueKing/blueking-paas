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

"""The Forgejo calls whose response body is streamed straight through to a caller.

A separate client rather than async methods on
:class:`~app_spark_api.infras.forgejo.client.ForgejoClient`, because the two have opposite
shapes. Provision is a sequence of short request/response pairs run from a synchronous
service under ``sync_to_async``, and it stays that way. An archive download is one long
response that has to be handed to the ASGI handler chunk by chunk, so it must run on the
event loop that handler is already on -- pushing it into a thread would pin a worker for
the whole transfer and buy nothing, since there is no CPU work to overlap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import httpx2

from app_spark_api.infras.forgejo.entities import ForgejoClientConfig, RemoteBranch
from app_spark_api.infras.forgejo.exceptions import ForgejoUnavailableError

if TYPE_CHECKING:
    from types import TracebackType


class ForgejoAsyncClient:
    """Forgejo API v1 reads, authenticated as the service account via Basic Auth.

    No repository token is minted for a read. The service account owns the Organization,
    so it can already see every Project repository; the tokens provision creates exist for
    the Agent, and the read-scoped one it issues is deleted as soon as its isolation has
    been verified.

    :param config: Connection settings for one Forgejo.
    :param transport: httpx transport; tests inject ``MockTransport``.
    """

    def __init__(
        self,
        config: ForgejoClientConfig,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._client = httpx2.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=config.timeout_seconds,
            transport=transport,
            auth=(config.username, config.password),
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def get_branch(self, owner: str, name: str, branch: str) -> RemoteBranch:
        """Return the branch and the commit its tip is at.

        A missing branch is a failure, not ``None``: every Project repository is created
        with ``auto_init``, so its working branch exists unless something broke.

        :raises ForgejoUnavailableError: Forgejo was unreachable, or has no such branch.
        """
        path = f"api/v1/repos/{owner}/{name}/branches/{branch}"
        response = await self._request("GET", path)
        self._raise_for_status(response, f"GET branch {owner}/{name} {branch}")
        return RemoteBranch.from_payload(response.json())

    async def open_archive(self, *, owner: str, name: str, ref: str, suffix: str) -> httpx2.Response:
        """Start downloading ``ref`` as an archive, leaving the body unread.

        The returned response has had its status checked but still has its bytes on the
        wire: the caller reads them with ``aiter_bytes()`` and owns ``aclose()``. Checking
        the status *here* is the point of the method -- it is the last moment at which a
        Forgejo failure can still become an ordinary error response, because once the
        caller starts writing the body the status line has been sent and the only
        remaining signal is a truncated file.

        :param owner: Organization the repository belongs to.
        :param name: Repository name.
        :param ref: Branch, tag, or commit to archive.
        :param suffix: Extension Forgejo picks the archive format by, e.g. ``zip``.
        :return: An open, successful response.
        :raises ForgejoUnavailableError: Forgejo was unreachable, or refused the read.
        """
        path = f"api/v1/repos/{owner}/{name}/archive/{ref}.{suffix}"
        # Override the client-wide JSON Accept: what comes back here is an archive, and a
        # future Forgejo that content-negotiates should not be told to send us a document.
        request = self._client.build_request("GET", path, headers={"Accept": "*/*"})
        try:
            response = await self._client.send(request, stream=True)
        except httpx2.HTTPError as exc:
            raise ForgejoUnavailableError(f"Forgejo request GET {path} failed: {exc}") from exc
        if response.is_success:
            return response
        raise ForgejoUnavailableError(
            f"GET archive {owner}/{name} {ref}.{suffix} failed: {await self._spend(response)}"
        )

    async def _spend(self, response: httpx2.Response) -> str:
        """Read and release a failed streaming response, returning it as a log line.

        The body has to be read before the connection is released, because it is the only
        description of the failure we will get -- and an unread streaming response cannot
        be inspected afterwards.
        """
        try:
            body = (await response.aread()).decode("utf-8", errors="replace")
        except httpx2.HTTPError as exc:
            body = f"<unreadable body: {exc}>"
        finally:
            await response.aclose()
        return f"HTTP {response.status_code} {body}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx2.Response:
        try:
            return await self._client.request(method, path, **kwargs)
        except httpx2.HTTPError as exc:
            raise ForgejoUnavailableError(f"Forgejo request {method} {path} failed: {exc}") from exc

    def _raise_for_status(self, response: httpx2.Response, action: str) -> None:
        if response.is_success:
            return
        raise ForgejoUnavailableError(f"{action} failed: HTTP {response.status_code} {response.text}")
