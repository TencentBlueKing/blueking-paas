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

"""Provision E2B sandboxes for Agent Runtimes.

Sandbox ownership is recorded in the database, so another API worker can reconnect after the
worker that created a sandbox exits. Installing and starting the Agent is still a separate step.
"""

from __future__ import annotations

import asyncio
import json
import secrets

from django.db import IntegrityError
from django.utils import timezone
from e2b import AsyncSandbox, NotFoundException, SandboxException
from e2b.connection_config import ConnectionConfig
from packaging.version import Version

from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, E2BConfig, GitRemote, StateCallback
from app_spark_api.agent.runtime.exceptions import AgentProvisionError, AgentWorkspaceBusyError
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider


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
        # Serialize requests in this worker. Nullable unique active IDs in the database also
        # keep workers from starting rival sandboxes for one conversation or Project workspace.
        self._lock = asyncio.Lock()

    async def ensure(
        self,
        *,
        project_id: str,
        conversation_id: str,
        state_callback: StateCallback | None = None,
        git_remote: GitRemote | None = None,
    ) -> AgentRuntimeHandle:
        """Return an existing sandbox or create one with a durable ownership record.

        The callback and Git remote become useful when the Agent process is installed and
        started inside the sandbox; this stage does not pass them to an Agent.

        :param project_id: Project whose conversations must not run concurrently.
        :param conversation_id: Conversation to assign to the sandbox.
        :param state_callback: Future Runtime state callback, unused at this stage.
        :param git_remote: Future workspace remote, unused at this stage.
        :return: Reserved HTTP endpoint and token for the future Runtime.
        :raises AgentProvisionError: If sandbox creation, reconnection, or recording fails.
        :raises AgentWorkspaceBusyError: If another conversation of this Project is active.
        """
        async with self._lock:
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            if record is not None:
                sandbox = await self._connect_active(record)
                if sandbox is not None:
                    return self._handle(record, sandbox)

            conflict = await E2BSandboxRecord.objects.active_for_project(project_id).afirst()
            if conflict is not None:
                sandbox = await self._connect_active(conflict)
                if sandbox is not None:
                    raise AgentWorkspaceBusyError(
                        f"Conversation {conflict.conversation_id} already has a running Agent on this project."
                    )

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

            try:
                info = await sandbox.get_info()
            except SandboxException as exc:
                await self._kill_unrecorded(sandbox)
                raise AgentProvisionError(f"Could not inspect the new E2B sandbox: {exc}") from exc

            try:
                record = await E2BSandboxRecord.objects.acreate(
                    sandbox_id=sandbox.sandbox_id,
                    project_id=project_id,
                    conversation_id=conversation_id,
                    active_project_id=project_id,
                    active_conversation_id=conversation_id,
                    runtime_token=secrets.token_urlsafe(32),
                    template=self.config.template,
                    sandbox_domain=info.sandbox_domain,
                    envd_version=info.envd_version,
                    sandbox_headers=json.dumps(dict(sandbox.connection_config.sandbox_headers), sort_keys=True),
                    traffic_access_token=sandbox.traffic_access_token,
                )
            except IntegrityError as exc:
                await self._kill_unrecorded(sandbox)
                # A competing API worker may have won the same conversation. Preserve ensure's
                # idempotency; a different conversation owning the Project is a real conflict.
                winner = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
                if winner is not None:
                    connected = await self._connect_active(winner)
                    if connected is not None:
                        return self._handle(winner, connected)
                conflict = await E2BSandboxRecord.objects.active_for_project(project_id).afirst()
                if conflict is not None and await self._connect_active(conflict) is not None:
                    raise AgentWorkspaceBusyError(f"Project {project_id} already has an active sandbox.") from exc
                raise AgentProvisionError(f"Could not record E2B sandbox {sandbox.sandbox_id}: {exc}") from exc
            except Exception:
                await self._kill_unrecorded(sandbox)
                raise
            return self._handle(record, sandbox)

    async def peek(self, conversation_id: str) -> AgentRuntimeHandle | None:
        """Reconnect to the sandbox serving a conversation without creating one.

        :param conversation_id: Conversation to inspect.
        :return: Its Runtime handle, or ``None`` if no live sandbox is recorded.
        :raises AgentProvisionError: If E2B cannot inspect the recorded sandbox.
        """
        async with self._lock:
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            if record is None:
                return None
            sandbox = await self._connect_active(record)
            return self._handle(record, sandbox) if sandbox is not None else None

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
        async with self._lock:
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            return await self._connect_active(record) if record is not None else None

    async def preview_upstream(self, conversation_id: str) -> str | None:
        """Return the exposed host for the sandbox's fixed workspace-app port.

        :param conversation_id: Conversation whose application is to be previewed.
        :return: Externally reachable base URL, or ``None`` without a live sandbox.
        :raises AgentProvisionError: If E2B cannot inspect the recorded sandbox.
        """
        async with self._lock:
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            if record is None:
                return None
            sandbox = await self._connect_active(record)
            if sandbox is None:
                return None
            return f"{self.config.port_scheme}://{sandbox.get_host(self.config.preview_port)}"

    async def terminate(self, conversation_id: str) -> None:
        """Stop the sandbox serving a conversation, retaining its historical record.

        :param conversation_id: Conversation whose sandbox should stop.
        :raises AgentProvisionError: If E2B could not stop the sandbox.
        """
        async with self._lock:
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            if record is not None:
                await self._terminate_record(record)

    async def shutdown(self) -> None:
        """Stop all active sandboxes owned by this API service.

        :raises AgentProvisionError: If an active sandbox could not be stopped.
        """
        async with self._lock:
            async for record in E2BSandboxRecord.objects.active():
                await self._terminate_record(record)

    async def _connect_active(self, record: E2BSandboxRecord) -> AsyncSandbox | None:
        """Reconnect using current settings, retiring records whose sandbox has vanished."""
        try:
            sandbox = await AsyncSandbox.connect(
                record.sandbox_id,
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
            )
        except NotFoundException:
            # Our self-hosted control plane answers 404 to `connect` for an already-running
            # sandbox. Rebuild the SDK object from its persisted connection metadata, then ask
            # envd whether it is still alive. Standard E2B can use the connect response above.
            try:
                sandbox = self._rebuild_sandbox(record)
            except (SandboxException, ValueError) as exc:
                raise AgentProvisionError(f"Could not rebuild E2B sandbox {record.sandbox_id}: {exc}") from exc
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not inspect E2B sandbox {record.sandbox_id}: {exc}") from exc

        try:
            if await sandbox.is_running():
                await self._refresh_connection(record, sandbox)
                return sandbox
        except NotFoundException:
            pass
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not inspect E2B sandbox {record.sandbox_id}: {exc}") from exc
        await self._release(record, "expired")
        return None

    def _rebuild_sandbox(self, record: E2BSandboxRecord) -> AsyncSandbox:
        headers = json.loads(record.sandbox_headers)
        if not isinstance(headers, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in headers.items()
        ):
            raise ValueError("Stored E2B sandbox headers are invalid")
        return AsyncSandbox(
            sandbox_id=record.sandbox_id,
            sandbox_domain=record.sandbox_domain,
            envd_version=Version(record.envd_version),
            envd_access_token=headers.get("X-Access-Token"),
            traffic_access_token=record.traffic_access_token,
            connection_config=ConnectionConfig(
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
                extra_sandbox_headers=headers,
            ),
        )

    @staticmethod
    async def _refresh_connection(record: E2BSandboxRecord, sandbox: AsyncSandbox) -> None:
        """Keep renewed access tokens after a successful standard SDK reconnect."""
        headers = dict(sandbox.connection_config.sandbox_headers)
        if (
            headers == json.loads(record.sandbox_headers)
            and sandbox.traffic_access_token == record.traffic_access_token
        ):
            return
        await E2BSandboxRecord.objects.filter(sandbox_id=record.sandbox_id).aupdate(
            sandbox_headers=json.dumps(headers, sort_keys=True),
            traffic_access_token=sandbox.traffic_access_token,
            sandbox_domain=sandbox.sandbox_domain,
            updated_at=timezone.now(),
        )
        record.sandbox_headers = json.dumps(headers, sort_keys=True)
        record.traffic_access_token = sandbox.traffic_access_token
        record.sandbox_domain = sandbox.sandbox_domain

    async def _terminate_record(self, record: E2BSandboxRecord) -> None:
        sandbox = await self._connect_active(record)
        if sandbox is None:
            return
        try:
            await sandbox.kill()
        except NotFoundException:
            pass
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not stop E2B sandbox {record.sandbox_id}: {exc}") from exc
        await self._release(record, "terminated")

    @staticmethod
    async def _release(record: E2BSandboxRecord, reason: str) -> None:
        stopped_at = timezone.now()
        await E2BSandboxRecord.objects.filter(
            sandbox_id=record.sandbox_id, active_conversation_id__isnull=False
        ).aupdate(
            active_project_id=None,
            active_conversation_id=None,
            stopped_at=stopped_at,
            stop_reason=reason,
            updated_at=stopped_at,
        )

    @staticmethod
    async def _kill_unrecorded(sandbox: AsyncSandbox) -> None:
        try:
            await sandbox.kill()
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not clean up unrecorded E2B sandbox: {exc}") from exc

    def _handle(self, record: E2BSandboxRecord, sandbox: AsyncSandbox) -> AgentRuntimeHandle:
        return AgentRuntimeHandle(
            conversation_id=record.conversation_id,
            base_url=f"{self.config.port_scheme}://{sandbox.get_host(self.config.runtime_port)}",
            runtime_token=record.runtime_token,
            http_headers=self._port_headers(sandbox),
        )

    @staticmethod
    def _port_headers(sandbox: AsyncSandbox) -> dict[str, str]:
        """Forward tokens required by the E2B proxy for an exposed application port."""
        headers: dict[str, str] = {}
        # The self-hosted proxy in front of our E2B service requires the same sandbox access
        # token the SDK sends to envd. Read it through the SDK's public connection config, not
        # through the sandbox's private token field. The port itself comes from get_host().
        if access_token := sandbox.connection_config.sandbox_headers.get("X-Access-Token"):
            headers["X-Access-Token"] = access_token
        if sandbox.traffic_access_token:
            headers["E2b-Traffic-Access-Token"] = sandbox.traffic_access_token
        return headers
