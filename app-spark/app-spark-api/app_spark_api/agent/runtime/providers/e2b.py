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

"""Provision E2B sandboxes for Agent Runtimes and start the Agent inside them."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import shlex
import time
import weakref
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, AsyncGenerator

from django.db import IntegrityError
from django.utils import timezone
from e2b import AsyncSandbox, NotFoundException, SandboxException
from e2b.connection_config import ConnectionConfig
from packaging.version import InvalidVersion, Version

from app_spark_api.agent.runtime.client import AgentRuntimeClient
from app_spark_api.agent.runtime.entities import (
    AgentRuntimeHandle,
    E2BConfig,
    GitRemote,
    ModelAccess,
    ModelAccessResolver,
    PreviewTarget,
    StateCallback,
)
from app_spark_api.agent.runtime.exceptions import (
    AgentProvisionError,
    AgentUnavailableError,
    AgentWorkspaceBusyError,
)
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.agent_env import build_agent_env
from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider

if TYPE_CHECKING:
    from e2b.sandbox_async.commands.command_handle import AsyncCommandHandle

logger = logging.getLogger(__name__)

# Upper bound on creating a sandbox and binding it to its claim. The whole step is bounded, not
# each request, because the SDK retries rate-limited requests; only a bounded step lets an old
# unbound claim be told apart from one that is still being provisioned.
PROVISION_TIMEOUT_SECONDS = 120

# An unbound claim older than this belongs to a worker that died while provisioning. The margin
# covers the database writes around the bounded step and clock skew between workers.
ABANDONED_CLAIM_SECONDS = PROVISION_TIMEOUT_SECONDS + 60

# A bound claim whose Agent has not been recorded as started for longer than the startup timeout
# plus this margin belongs to a worker that died while starting it. The margin covers opening the
# command stream, reading the failure log, and clock skew between workers.
STARTUP_GRACE_MARGIN_SECONDS = 60

# Each /health probe goes through the E2B port proxy, so it is given longer than a loopback
# probe; the whole wait is still bounded by E2BConfig.startup_timeout_seconds.
HEALTH_POLL_INTERVAL_SECONDS = 0.5
HEALTH_PROBE_TIMEOUT_SECONDS = 3.0

# How much of a failed Agent's own log to quote back. A configuration error kills it during
# import, and its traceback is the only thing that can say why.
LOG_TAIL_LINES = 40


async def probe_agent_health(
    handle: AgentRuntimeHandle, *, timeout_seconds: float = HEALTH_PROBE_TIMEOUT_SECONDS
) -> bool:
    """Tell whether the Runtime behind ``handle`` answers ``/health`` yet.

    :param handle: Where the Runtime should be reachable.
    :param timeout_seconds: Upper bound on this one probe.
    :return: Whether it answered with a usable health snapshot.
    """
    try:
        await AgentRuntimeClient(handle, timeout_seconds=timeout_seconds).health()
    except AgentUnavailableError:
        return False
    return True


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
    """Allocate one E2B sandbox per conversation, start its Agent Runtime, and retain its record.

    Example::

        provider = E2BProvider(
            E2BConfig(
                api_key="...",
                api_url="https://example.com/e2b",
                callback_base_url="https://app-spark.example.com",
            )
        )
        handle = await provider.ensure(
            project_id="project",
            conversation_id="conversation",
            model_access=lambda: resolve_model_access(credential),
        )
        await provider.shutdown()

    :param config: E2B API, sandbox, and Agent start settings.
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
        model_access: ModelAccessResolver | None = None,
    ) -> AgentRuntimeHandle:
        """Return an existing sandbox or claim the conversation, create one, and start its Agent.

        :param project_id: Project whose conversations must not run concurrently.
        :param conversation_id: Conversation to assign to the sandbox.
        :param state_callback: Where the started Runtime replicates its state.
        :param git_remote: Where the started Runtime persists its workspace.
        :param model_access: Returns how the started Runtime calls its model. Called only when a
            sandbox is about to be created, so reusing a running Runtime costs no token exchange.
        :return: Endpoint and token of a Runtime that has answered ``/health``.
        :raises AgentProvisionError: If no model access was given, or sandbox creation,
            reconnection, recording, or the Agent's start fails.
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

            # 在锁里、确定要新建之后，且在占位之前解析：已在跑的 Runtime 不花一次换票；换票失败时
            # 既没有沙箱也没有占位要收拾。代价是另一个 worker 抢先占位时，这次换票白做了。
            if model_access is None:
                raise AgentProvisionError("Starting an Agent Runtime needs model access, and none was given.")
            access = await model_access()

            claim = _SandboxClaim(
                await self._claim(project_id=project_id, conversation_id=conversation_id), self.config
            )
            sandbox = None
            try:
                try:
                    async with asyncio.timeout(PROVISION_TIMEOUT_SECONDS):
                        sandbox = await self._create_sandbox()
                        await claim.bind(sandbox)
                except TimeoutError as exc:
                    raise AgentProvisionError(
                        f"Provisioning an E2B sandbox took longer than {PROVISION_TIMEOUT_SECONDS} seconds."
                    ) from exc

                # Outside the provisioning bound: the claim is bound by now, so it can no longer
                # be mistaken for an abandoned one, and starting the Agent has a bound of its own.
                await self._prepare_sandbox(sandbox)
                handle = claim.handle(sandbox)
                envs = self._build_agent_env(
                    project_id=project_id,
                    runtime_token=handle.runtime_token,
                    state_callback=state_callback,
                    git_remote=git_remote,
                    model_access=access,
                )
                await claim.start_agent(sandbox, handle, envs)
            except BaseException:
                # Cancellation included: the claim is this request's to give back, and so is
                # a sandbox it has already created, together with any Agent started in it.
                await claim.abandon(sandbox)
                raise
            return handle

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
            sandbox is bound to the conversation or its Agent has not started yet.
        :raises AgentProvisionError: If the stored connection metadata is unusable.
        """
        record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
        if record is None or not record.is_started:
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

    async def _prepare_sandbox(self, sandbox: AsyncSandbox) -> None:
        """Make a freshly bound sandbox able to run the Agent before it is started.

        The production template already contains the Agent, so there is nothing to do. The live
        tests override this to install a locally built Agent into the default template.

        :param sandbox: The sandbox about to have its Agent started.
        """

    async def _create_sandbox(self) -> AsyncSandbox:
        """Ask E2B for a sandbox from the configured template.

        :raises AgentProvisionError: If E2B refuses or fails to create one.
        """
        try:
            return await AsyncSandbox.create(
                self.config.template,
                timeout=self.config.timeout_seconds,
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
            )
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not create an E2B sandbox: {exc}") from exc

    def _build_agent_env(
        self,
        *,
        project_id: str,
        runtime_token: str,
        state_callback: StateCallback | None,
        git_remote: GitRemote | None,
        model_access: ModelAccess,
    ) -> dict[str, str]:
        """Build the Agent's whole environment; nothing of this service's own is inherited."""
        config = self.config

        # 沙箱经 Ingress 回调本服务，公开前缀（FORCE_SCRIPT_NAME）必须保留；只有走回环、绕过
        # Ingress 的 local provider 才去掉它。
        control_plane_url = None
        if state_callback is not None:
            control_plane_url = f"{config.callback_base_url.rstrip('/')}{state_callback.path}"

        return build_agent_env(
            workspace=config.workspace_dir,
            state_dir=config.state_dir,
            runtime_token=runtime_token,
            project_id=project_id,
            # 两个端口都显式给：镜像里 Agent 的默认应用端口 8000 恰好等于默认的 runtime_port。
            port=config.runtime_port,
            app_port=config.preview_port,
            model_access=model_access,
            extra_env=config.extra_env,
            control_plane_url=control_plane_url,
            state_callback=state_callback,
            git_remote=git_remote,
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

    async def start_agent(self, sandbox: AsyncSandbox, handle: AgentRuntimeHandle, envs: dict[str, str]) -> None:
        """Start the Agent Runtime in a bound sandbox and return once it answers ``/health``.

        :param sandbox: The sandbox bound to this claim.
        :param handle: Where the Runtime will be reachable, used to probe it.
        :param envs: The Agent's whole environment. Passed to this one process through envd, not
            to the sandbox at creation, so no credential travels through the control plane.
        :raises AgentProvisionError: If the Agent cannot be started, exits during startup, never
            becomes healthy, or the claim was released meanwhile.
        """
        config = self.config
        # The Agent creates its state directory itself, but not the parent of it. `exec` makes the
        # recorded pid the Agent's own rather than a wrapping shell's, so a later stop signals
        # the process that has a workspace to push. The redirect covers the whole group, so a
        # failing mkdir explains itself in the same log as the Agent would.
        state_parent = str(PurePosixPath(config.state_dir).parent)
        command = (
            f"{{ mkdir -p {shlex.quote(config.workspace_dir)} {shlex.quote(state_parent)}"
            f" && exec {config.agent_command}; }} >> {shlex.quote(config.agent_log_path)} 2>&1"
        )
        try:
            process = await sandbox.commands.run(command, background=True, envs=envs, timeout=0)
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not start the Agent in E2B sandbox {sandbox.sandbox_id}: {exc}") from exc

        try:
            await self._wait_until_healthy(sandbox, process, handle)
            # Only after /health: the pid is also the mark other requests go by before they hand
            # this sandbox out, so writing it earlier would hand out a port nobody answers yet.
            await self._record_agent_pid(process.pid)
        finally:
            # The event stream is only needed while starting; the request must not keep holding
            # it. Disconnecting leaves the Agent itself running.
            await process.disconnect()

    async def _record_agent_pid(self, pid: int) -> None:
        """Mark the claim started by recording its healthy Agent's pid, if the claim is still active.

        :raises AgentProvisionError: If the claim was released while the Agent was starting.
        """
        record = self.record
        updated = await E2BSandboxRecord.objects.filter(pk=record.pk, active_conversation_id__isnull=False).aupdate(
            agent_pid=pid, updated_at=timezone.now()
        )
        if not updated:
            raise AgentProvisionError(
                f"The sandbox claim of conversation {record.conversation_id} was released while its Agent was starting."
            )
        record.agent_pid = pid

    async def _wait_until_healthy(
        self, sandbox: AsyncSandbox, process: AsyncCommandHandle, handle: AgentRuntimeHandle
    ) -> None:
        """Poll ``/health`` until the Agent answers, or explain why it never will."""
        deadline = time.monotonic() + self.config.startup_timeout_seconds
        while True:
            # Checked on every pass, not only at the deadline: a bad configuration kills the Agent
            # during import, and saying so at once beats polling something that already exited.
            # Being first in the loop also means an Agent that exits during the last probe is
            # reported with its exit code rather than as a timeout.
            if process.exit_code is not None:
                raise AgentProvisionError(
                    f"The Agent Runtime exited during startup with code {process.exit_code}:\n"
                    f"{await self._read_failure_output(sandbox, process)}"
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AgentProvisionError(
                    f"The Agent Runtime never became healthy within {self.config.startup_timeout_seconds} seconds:\n"
                    f"{await self._read_failure_output(sandbox, process)}"
                )

            # One probe never outlasts the time left, so the wait does not overrun the configured
            # timeout by a probe's length.
            if await probe_agent_health(handle, timeout_seconds=min(HEALTH_PROBE_TIMEOUT_SECONDS, remaining)):
                return
            await asyncio.sleep(min(HEALTH_POLL_INTERVAL_SECONDS, max(deadline - time.monotonic(), 0)))

    async def _read_failure_output(self, sandbox: AsyncSandbox, process: AsyncCommandHandle) -> str:
        """Return the end of what a failed start wrote, for a failure that has to be explained."""
        try:
            content = str(await sandbox.files.read(self.config.agent_log_path))
        except SandboxException:
            content = ""
        # The log file holds nothing when the shell could not even open it (an unwritable log
        # directory); what the shell said about that is in the command's own output instead.
        if not content.strip():
            content = f"{process.stdout}{process.stderr}"
        lines = content.splitlines()[-LOG_TAIL_LINES:]
        return "\n".join(lines) if lines else "(the Agent Runtime wrote no output)"

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
        # A sandbox whose Agent is still starting is stopped all the same; the request starting
        # it then finds its claim released when it goes to record the Agent.
        sandbox = await self.connect(reconcile=True, require_started=False)
        if sandbox is None:
            return
        try:
            await sandbox.kill()
        except NotFoundException:
            pass
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not stop E2B sandbox {record.sandbox_id}: {exc}") from exc
        await self._release("terminated")

    async def connect(self, *, reconcile: bool, require_started: bool = True) -> AsyncSandbox | None:
        """Reconnect to a record's sandbox if it is still running.

        :param reconcile: Also write back what was learned: renewed tokens of a live sandbox,
            and release of a sandbox that has gone or of a claim nobody came back to bind or
            start. Only paths about to act on the answer pass ``True``. Read-only paths leave
            the record alone, so one failed check during a status poll cannot give away a live
            sandbox.
        :param require_started: Treat a sandbox whose Agent has not answered /health yet as not
            serving. Only stopping a sandbox wants it regardless.
        :return: The connected sandbox, or ``None`` if it is not running, not created yet, or
            (when required) its Agent has not started.
        :raises AgentWorkspaceBusyError: When reconciling a claim another request is still
            provisioning, or whose Agent another request is still starting.
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

        # Bound but not started: another request, possibly on another worker, is still starting
        # the Agent, or died doing so. Its sandbox answers nothing yet, and a failed start makes
        # that request kill it, so handing it out now would hand out a dead end.
        if require_started and not record.is_started and (not reconcile or await self._give_up_unstarted_claim()):
            return None

        sandbox = await self._open_sandbox(sandbox_id)
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

    async def _open_sandbox(self, sandbox_id: str) -> AsyncSandbox:
        """Get an SDK object for the record's sandbox, without saying whether it still runs.

        :raises AgentProvisionError: If E2B cannot be asked, or the stored metadata is unusable.
        """
        try:
            return await AsyncSandbox.connect(
                sandbox_id,
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
            )
        except NotFoundException:
            # Our self-hosted control plane answers 404 to `connect` for an already-running
            # sandbox. Rebuild the SDK object from its persisted connection metadata; callers
            # then ask envd whether it is still alive. Standard E2B can use the response above.
            try:
                return self.rebuild_sandbox()
            except (SandboxException, ValueError) as exc:
                raise AgentProvisionError(f"Could not rebuild E2B sandbox {sandbox_id}: {exc}") from exc
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not inspect E2B sandbox {sandbox_id}: {exc}") from exc

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

    async def _give_up_unstarted_claim(self) -> bool:
        """Release a bound claim whose Agent never started, unless it started since the read.

        :return: Whether the caller is done with it. ``False`` means the Agent was recorded as
            started meanwhile and ``record`` has been refreshed into that started, active row.
        :raises AgentWorkspaceBusyError: If the claim is recent enough to still be starting.
        """
        record = self.record
        # `updated_at` was last written by the bind, which is when starting the Agent began.
        grace = self.config.startup_timeout_seconds + STARTUP_GRACE_MARGIN_SECONDS
        if record.updated_at > timezone.now() - timedelta(seconds=grace):
            raise AgentWorkspaceBusyError(
                f"Conversation {record.conversation_id} is still starting its Agent on this project."
            )

        # Released only while still unstarted: an Agent recorded as started this very moment
        # belongs to a request that is about to return it, and must not lose its sandbox.
        if await self._release("abandoned", only_unstarted=True):
            await self._kill_quietly()
            return True
        await record.arefresh_from_db()
        return record.active_conversation_id is None

    async def _kill_quietly(self) -> None:
        """Kill the recorded sandbox, best effort: a missed one still ends at its E2B timeout."""
        record = self.record
        if record.sandbox_id is None:
            return
        try:
            sandbox = await self._open_sandbox(record.sandbox_id)
            await sandbox.kill()
        except AgentProvisionError, SandboxException:
            logger.warning(
                "Could not kill E2B sandbox %s whose Agent never started; it runs until its E2B timeout",
                record.sandbox_id,
                exc_info=True,
            )

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

    async def _release(self, reason: str, *, only_unbound: bool = False, only_unstarted: bool = False) -> bool:
        """Clear a claim's active IDs.

        :param reason: Why it is ending, kept on the row for history.
        :param only_unbound: Also require that no sandbox has been recorded yet. A bind that
            won the race then keeps the claim, and the caller reconnects to stop that sandbox.
        :param only_unstarted: Also require that no Agent has been recorded as started. A start
            that won the race then keeps the claim, and the request that started it returns it.
        :return: Whether this call released the claim.
        """
        record = self.record
        stopped_at = timezone.now()
        query = E2BSandboxRecord.objects.filter(pk=record.pk, active_conversation_id__isnull=False)
        if only_unbound:
            query = query.filter(sandbox_id__isnull=True)
        if only_unstarted:
            query = query.filter(agent_pid__isnull=True)
        released = await query.aupdate(
            active_project_id=None,
            active_conversation_id=None,
            stopped_at=stopped_at,
            stop_reason=reason,
            updated_at=stopped_at,
        )
        return bool(released)
