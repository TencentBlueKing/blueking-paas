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

"""Provision E2B sandboxes for Agent Runtimes."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import weakref
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator

from django.db import IntegrityError
from django.utils import timezone
from e2b import AsyncSandbox, NotFoundException, SandboxException
from e2b.connection_config import ConnectionConfig
from packaging.version import InvalidVersion, Version

from app_spark_api.agent.runtime.entities import (
    AgentRuntimeHandle,
    E2BConfig,
    GitRemote,
    PreviewTarget,
    StateCallback,
)
from app_spark_api.agent.runtime.exceptions import AgentProvisionError, AgentWorkspaceBusyError
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider

logger = logging.getLogger(__name__)

# Upper bound on creating a sandbox and binding it to its claim. The whole step is bounded, not
# each request, because the SDK retries rate-limited requests; only a bounded step lets an old
# unbound claim be told apart from one that is still being provisioned.
PROVISION_TIMEOUT_SECONDS = 120

# An unbound claim older than this belongs to a worker that died while provisioning. The margin
# covers the database writes around the bounded step and clock skew between workers.
ABANDONED_CLAIM_SECONDS = PROVISION_TIMEOUT_SECONDS + 60


def _port_headers(sandbox: AsyncSandbox) -> dict[str, str]:
    """Forward tokens required by the E2B proxy for an exposed application port."""
    headers: dict[str, str] = {}
    # The self-hosted proxy in front of our E2B service requires the same sandbox access
    # token the SDK sends to envd. Read it through the SDK's public connection config, not
    # through the sandbox's private token field. The port itself comes from get_host().
    if access_token := sandbox.connection_config.sandbox_headers.get("X-Access-Token"):
        headers["X-Access-Token"] = access_token
    if sandbox.traffic_access_token:
        headers["E2B-Traffic-Access-Token"] = sandbox.traffic_access_token
    return headers


class E2BProvider(AgentRuntimeProvider):
    """Allocate one E2B sandbox per conversation and retain its record.

    Example::

        provider = E2BProvider(E2BConfig(api_key="...", api_url="https://example.com/e2b"))
        handle = await provider.ensure(project_id="project", conversation_id="conversation")
        await provider.shutdown()

    :param config: E2B API and sandbox settings.
    """

    def __init__(self, config: E2BConfig) -> None:
        self.config = config
        # One lock per conversation.
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    async def ensure(
        self,
        *,
        project_id: str,
        conversation_id: str,
        state_callback: StateCallback | None = None,
        git_remote: GitRemote | None = None,
    ) -> AgentRuntimeHandle:
        """Return an existing sandbox or claim the conversation and create one.

        The callback and Git remote become useful when the Agent process is installed and
        started inside the sandbox; this stage does not pass them to an Agent.

        :param project_id: Project whose conversations must not run concurrently.
        :param conversation_id: Conversation to assign to the sandbox.
        :param state_callback: Future Runtime state callback, unused at this stage.
        :param git_remote: Future workspace remote, unused at this stage.
        :return: Reserved HTTP endpoint and token for the future Runtime.
        :raises AgentProvisionError: If sandbox creation, reconnection, or recording fails.
        :raises AgentWorkspaceBusyError: If another conversation of this Project is active, or
            another worker is still creating a sandbox for this conversation or Project.
        """
        async with self._conversation_lock(conversation_id):
            if active := await self._active_sandbox(conversation_id, reconcile=True):
                claim, existing_sandbox = active
                return claim.handle(existing_sandbox)

            # A holder whose sandbox has gone is released here, so the claim below can succeed.
            holder = await E2BSandboxRecord.objects.active_for_project(project_id).afirst()
            if holder is not None and await _SandboxClaim(holder, self.config).connect(reconcile=True) is not None:
                raise AgentWorkspaceBusyError(
                    f"Conversation {holder.conversation_id} already has a running Agent on this project."
                )

            claim = _SandboxClaim(
                await self._claim(project_id=project_id, conversation_id=conversation_id), self.config
            )
            sandbox = None
            try:
                async with asyncio.timeout(PROVISION_TIMEOUT_SECONDS):
                    try:
                        sandbox = await AsyncSandbox.create(
                            self.config.template,
                            timeout=self.config.timeout_seconds,
                            api_key=self.config.api_key,
                            api_url=self.config.api_url,
                            domain=self.config.domain,
                        )
                    except SandboxException as exc:
                        raise AgentProvisionError(f"Could not create an E2B sandbox: {exc}") from exc
                    await claim.bind(sandbox)
                    return claim.handle(sandbox)
            except BaseException as exc:
                # Cancellation included: the claim is this request's to give back, and so is
                # a sandbox it has already created.
                await claim.abandon(sandbox)
                if isinstance(exc, TimeoutError):
                    raise AgentProvisionError(
                        f"Provisioning an E2B sandbox took longer than {PROVISION_TIMEOUT_SECONDS} seconds."
                    ) from exc
                raise

    async def terminate(self, conversation_id: str) -> None:
        """Stop the sandbox serving a conversation, retaining its historical record.

        :param conversation_id: Conversation whose sandbox should stop.
        :raises AgentProvisionError: If E2B could not stop the sandbox.
        """
        async with self._conversation_lock(conversation_id):
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            if record is not None:
                await _SandboxClaim(record, self.config).terminate()

    async def shutdown(self) -> None:
        """Stop all active sandboxes owned by this API service.

        :raises AgentProvisionError: If an active sandbox could not be stopped.
        """
        records = [record async for record in E2BSandboxRecord.objects.active()]
        for record in records:
            async with self._conversation_lock(record.conversation_id):
                await _SandboxClaim(record, self.config).terminate()

    async def peek(self, conversation_id: str) -> AgentRuntimeHandle | None:
        """Reconnect to the sandbox serving a conversation without creating or releasing one.

        :param conversation_id: Conversation to inspect.
        :return: Its Runtime handle, or ``None`` if no live sandbox is recorded.
        :raises AgentProvisionError: If E2B cannot inspect the recorded sandbox.
        """
        active = await self._active_sandbox(conversation_id)
        if active is None:
            return None
        claim, sandbox = active
        return claim.handle(sandbox)

    async def get_sandbox(self, conversation_id: str) -> AsyncSandbox | None:
        """Reconnect to a recorded sandbox for installation or inspection.

        Example::

            sandbox = await provider.get_sandbox(conversation_id)
            if sandbox is not None:
                await sandbox.commands.run("pwd")

        :param conversation_id: Conversation owning the sandbox.
        :return: Connected SDK sandbox, or ``None`` when no live sandbox is recorded.
        :raises AgentProvisionError: If the recorded sandbox cannot be inspected.
        """
        active = await self._active_sandbox(conversation_id)
        return active[1] if active is not None else None

    async def preview_target(self, conversation_id: str) -> PreviewTarget | None:
        """Return the exposed host for the sandbox's fixed workspace-app port.

        Answered from the record alone, without asking E2B whether the sandbox is still up:
        every asset of a previewed page comes through here. The host and the proxy tokens are
        fixed for a sandbox's lifetime, and a sandbox that has gone makes the proxied request
        fail as unreachable, which is the truthful answer anyway.

        :param conversation_id: Conversation whose application is to be previewed.
        :return: Externally reachable base URL and port-proxy headers, or ``None`` when no
            sandbox is bound to the conversation.
        :raises AgentProvisionError: If the stored connection metadata is unusable.
        """
        record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
        if record is None or record.sandbox_id is None:
            return None
        try:
            sandbox = _SandboxClaim(record, self.config).rebuild_sandbox()
        except (SandboxException, ValueError) as exc:
            raise AgentProvisionError(f"Could not rebuild E2B sandbox {record.sandbox_id}: {exc}") from exc
        return PreviewTarget(
            base_url=f"{self.config.port_scheme}://{sandbox.get_host(self.config.preview_port)}",
            http_headers=_port_headers(sandbox),
            # Our self-hosted E2B port proxy rejects a forwarded host different from its
            # exposed-port host with HTTP 400 (`bad target`).
            send_forwarded_host=False,
        )

    @asynccontextmanager
    async def _conversation_lock(self, conversation_id: str) -> AsyncGenerator[None]:
        lock = self._locks.get(conversation_id)
        if lock is None:
            lock = self._locks[conversation_id] = asyncio.Lock()
        async with lock:
            yield

    async def _active_sandbox(
        self, conversation_id: str, *, reconcile: bool = False
    ) -> tuple[_SandboxClaim, AsyncSandbox] | None:
        """Look up a conversation's active record and reconnect to its running sandbox."""
        record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
        if record is None:
            return None
        claim = _SandboxClaim(record, self.config)
        sandbox = await claim.connect(reconcile=reconcile)
        return (claim, sandbox) if sandbox is not None else None

    async def _claim(self, *, project_id: str, conversation_id: str) -> E2BSandboxRecord:
        """Reserve the conversation and its Project before any sandbox exists."""
        try:
            return await E2BSandboxRecord.objects.acreate(
                project_id=project_id,
                conversation_id=conversation_id,
                active_project_id=project_id,
                active_conversation_id=conversation_id,
                runtime_token=secrets.token_urlsafe(32),
                template=self.config.template,
            )
        except IntegrityError as exc:
            # Another worker claimed this conversation or Project after the checks in ensure.
            # It is creating a sandbox or already serving one; either way this request must not.
            raise AgentWorkspaceBusyError(
                f"Another request is already starting a sandbox for conversation {conversation_id} "
                f"or project {project_id}."
            ) from exc


class _SandboxClaim:
    """Operate on one recorded claim and its E2B sandbox.

    Each instance is scoped to one provider operation. Its record may be stale after another
    worker acts, so state transitions must still be conditional database updates.
    """

    def __init__(self, record: E2BSandboxRecord, config: E2BConfig) -> None:
        self.record = record
        self.config = config

    async def bind(self, sandbox: AsyncSandbox) -> None:
        """Record a newly created sandbox on its claim.

        :raises AgentProvisionError: If the sandbox cannot be inspected, or the claim was
            released while E2B was creating the sandbox.
        """
        claim = self.record
        try:
            info = await sandbox.get_info()
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not inspect the new E2B sandbox {sandbox.sandbox_id}: {exc}") from exc

        fields = {
            "sandbox_id": sandbox.sandbox_id,
            "sandbox_domain": info.sandbox_domain,
            "envd_version": info.envd_version,
            "sandbox_headers": json.dumps(dict(sandbox.connection_config.sandbox_headers), sort_keys=True),
            "traffic_access_token": sandbox.traffic_access_token,
        }
        # Conditional on the claim still being active: a terminate() on another worker, or a
        # request that judged this claim abandoned, may have released it in the meantime.
        bound = await E2BSandboxRecord.objects.filter(pk=claim.pk, active_conversation_id__isnull=False).aupdate(
            **fields, updated_at=timezone.now()
        )
        if not bound:
            raise AgentProvisionError(
                f"The sandbox claim of conversation {claim.conversation_id} was released while "
                f"E2B sandbox {sandbox.sandbox_id} was being created."
            )
        for name, value in fields.items():
            setattr(claim, name, value)

    async def abandon(self, sandbox: AsyncSandbox | None) -> None:
        """Give back a failed claim and the sandbox it may have created.

        Best-effort on both counts, so the failure that led here is the one the caller sees. A
        sandbox left running still ends at its E2B timeout, and a claim left active is taken for
        abandoned once it is older than :data:`ABANDONED_CLAIM_SECONDS`.
        """
        claim = self.record
        if sandbox is not None:
            try:
                await sandbox.kill()
            except SandboxException:
                logger.warning(
                    "Could not kill E2B sandbox %s after provisioning failed; it runs until its E2B timeout",
                    sandbox.sandbox_id,
                    exc_info=True,
                )
        try:
            await self._release("failed")
        except Exception:
            logger.exception(
                "Could not release the sandbox claim of conversation %s; it is reclaimed after %d seconds",
                claim.conversation_id,
                ABANDONED_CLAIM_SECONDS,
            )

    async def terminate(self) -> None:
        """Stop this claim's sandbox, preserving the record for history."""
        record = self.record
        if record.sandbox_id is None:
            # Nothing to stop yet, unless a bind landed after this record was read. Releasing
            # only while still unbound leaves that sandbox claimed, so the fall-through below
            # reconnects and stops it instead of forgetting it.
            if await self._release("terminated", only_unbound=True):
                return
            await record.arefresh_from_db()
            if record.sandbox_id is None or record.active_conversation_id is None:
                return
        sandbox = await self.connect(reconcile=True)
        if sandbox is None:
            return
        try:
            await sandbox.kill()
        except NotFoundException:
            pass
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not stop E2B sandbox {record.sandbox_id}: {exc}") from exc
        await self._release("terminated")

    async def connect(self, *, reconcile: bool) -> AsyncSandbox | None:
        """Reconnect to a record's sandbox if it is still running.

        :param reconcile: Also write back what was learned: renewed tokens of a live sandbox,
            and release of a sandbox that has gone or of a claim nobody came back to bind. Only
            paths about to act on the answer pass ``True``. Read-only paths leave the record
            alone, so one failed check during a status poll cannot give away a live sandbox.
        :return: The connected sandbox, or ``None`` if it is not running or not created yet.
        :raises AgentWorkspaceBusyError: When reconciling a claim another request is still
            provisioning.
        :raises AgentProvisionError: If E2B cannot say whether the sandbox is running.
        """
        record = self.record
        if record.sandbox_id is None and (not reconcile or await self._give_up_unbound_claim()):
            return None
        # Still empty after the claim was settled: it was released, or it never had a sandbox.
        # The bound case falls through with the id the refresh just loaded.
        sandbox_id = record.sandbox_id
        if sandbox_id is None:
            return None

        try:
            sandbox = await AsyncSandbox.connect(
                sandbox_id,
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
            )
        except NotFoundException:
            # Our self-hosted control plane answers 404 to `connect` for an already-running
            # sandbox. Rebuild the SDK object from its persisted connection metadata, then ask
            # envd whether it is still alive. Standard E2B can use the connect response above.
            try:
                sandbox = self.rebuild_sandbox()
            except (SandboxException, ValueError) as exc:
                raise AgentProvisionError(f"Could not rebuild E2B sandbox {record.sandbox_id}: {exc}") from exc
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not inspect E2B sandbox {record.sandbox_id}: {exc}") from exc

        try:
            if await sandbox.is_running():
                if reconcile:
                    await self._refresh_connection(sandbox)
                return sandbox
        except NotFoundException:
            pass
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not inspect E2B sandbox {record.sandbox_id}: {exc}") from exc
        if reconcile:
            await self._release("expired")
        return None

    def rebuild_sandbox(self) -> AsyncSandbox:
        """Build an SDK object from the record alone; nothing here reaches the network.

        :raises ValueError: If the record is unbound or its stored metadata is malformed.
        """
        record = self.record
        if record.sandbox_id is None or record.envd_version is None:
            raise ValueError("The record has no sandbox bound to it")
        headers = json.loads(record.sandbox_headers)
        if not isinstance(headers, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in headers.items()
        ):
            raise ValueError("Stored E2B sandbox headers are invalid")
        try:
            envd_version = Version(record.envd_version)
        except InvalidVersion as exc:
            raise ValueError(f"Stored envd version {record.envd_version!r} is invalid") from exc
        return AsyncSandbox(
            sandbox_id=record.sandbox_id,
            sandbox_domain=record.sandbox_domain,
            envd_version=envd_version,
            envd_access_token=headers.get("X-Access-Token"),
            traffic_access_token=record.traffic_access_token,
            connection_config=ConnectionConfig(
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
                extra_sandbox_headers=headers,
            ),
        )

    def handle(self, sandbox: AsyncSandbox) -> AgentRuntimeHandle:
        """Build the runtime endpoint using this claim's identity and transport."""
        record = self.record
        return AgentRuntimeHandle(
            conversation_id=record.conversation_id,
            base_url=f"{self.config.port_scheme}://{sandbox.get_host(self.config.runtime_port)}",
            runtime_token=record.runtime_token,
            http_headers=_port_headers(sandbox),
        )

    async def _give_up_unbound_claim(self) -> bool:
        """Release a claim that never received a sandbox, unless one was bound since the read.

        :return: Whether the caller is done with it. ``False`` means a bind won the race and
            ``record`` has been refreshed into that bound, still-active row.
        :raises AgentWorkspaceBusyError: If the claim is recent enough to still be provisioning.
        """
        record = self.record
        if record.created_at > timezone.now() - timedelta(seconds=ABANDONED_CLAIM_SECONDS):
            raise AgentWorkspaceBusyError(
                f"Conversation {record.conversation_id} is still starting a sandbox on this project."
            )
        # Releasing by primary key alone would drop a live sandbox's claim and leave that
        # sandbox running with nobody recorded to stop it.
        if await self._release("abandoned", only_unbound=True):
            return True
        await record.arefresh_from_db()
        return record.sandbox_id is None or record.active_conversation_id is None

    async def _refresh_connection(self, sandbox: AsyncSandbox) -> None:
        """Keep renewed access tokens after a successful standard SDK reconnect."""
        record = self.record
        headers = dict(sandbox.connection_config.sandbox_headers)
        if (
            headers == json.loads(record.sandbox_headers)
            and sandbox.traffic_access_token == record.traffic_access_token
        ):
            return
        await E2BSandboxRecord.objects.filter(pk=record.pk).aupdate(
            sandbox_headers=json.dumps(headers, sort_keys=True),
            traffic_access_token=sandbox.traffic_access_token,
            sandbox_domain=sandbox.sandbox_domain,
            updated_at=timezone.now(),
        )
        record.sandbox_headers = json.dumps(headers, sort_keys=True)
        record.traffic_access_token = sandbox.traffic_access_token
        record.sandbox_domain = sandbox.sandbox_domain

    async def _release(self, reason: str, *, only_unbound: bool = False) -> bool:
        """Clear a claim's active IDs.

        :param reason: Why it is ending, kept on the row for history.
        :param only_unbound: Also require that no sandbox has been recorded yet. A bind that
            won the race then keeps the claim, and the caller reconnects to stop that sandbox.
        :return: Whether this call released the claim.
        """
        record = self.record
        stopped_at = timezone.now()
        query = E2BSandboxRecord.objects.filter(pk=record.pk, active_conversation_id__isnull=False)
        if only_unbound:
            query = query.filter(sandbox_id__isnull=True)
        released = await query.aupdate(
            active_project_id=None,
            active_conversation_id=None,
            stopped_at=stopped_at,
            stop_reason=reason,
            updated_at=stopped_at,
        )
        return bool(released)
