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

"""Allocate one E2B sandbox per conversation and start its Agent."""

from __future__ import annotations

import asyncio
import logging
import secrets
import weakref
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from django.db import IntegrityError
from e2b import AsyncSandbox, SandboxException

from app_spark_api.agent.runtime.entities import (
    AgentRuntimeHandle,
    E2BConfig,
    GitRemote,
    ModelAccess,
    ModelAccessResolver,
    PreviewTarget,
    RuntimeHealth,
    StateCallback,
)
from app_spark_api.agent.runtime.exceptions import AgentProvisionError, AgentWorkspaceBusyError
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.agent_env import build_agent_env
from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider

from . import constants
from . import health as agent_health
from .claim import _SandboxClaim
from .lifetime import SandboxLifetime

logger = logging.getLogger(__name__)


class E2BProvider(AgentRuntimeProvider):
    """Allocate one E2B sandbox per conversation, start its Agent Runtime, and retain its record.

    Example::

        provider = E2BProvider(
            E2BConfig(
                api_key="...",
                api_url="https://example.com/e2b",
                callback_base_url="https://app-spark.example.com",
                template="app-spark-agent",
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
        self._lifetime = SandboxLifetime(config)
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
            reconnection, recording, the Agent's start, or retiring an unusable sandbox fails.
        :raises AgentWorkspaceBusyError: If another conversation of this Project is active, or
            another worker is still creating a sandbox for this conversation or Project.
        """
        async with self._conversation_lock(conversation_id):
            if active := await self._active_sandbox(conversation_id, reconcile=True):
                claim, existing_sandbox = active
                existing_handle = claim.handle(existing_sandbox)

                # ensure 只在一轮对话开始时调用，所以这里的续期就是「本轮开始算活动」。
                if await self._keep_for_next_turn(claim, existing_sandbox, existing_handle):
                    await self._renew_sandbox(claim.record.sandbox_id)
                    return existing_handle

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
                    async with asyncio.timeout(constants.PROVISION_TIMEOUT_SECONDS):
                        sandbox = await self._create_sandbox()
                        await claim.bind(sandbox)
                except TimeoutError as exc:
                    raise AgentProvisionError(
                        f"Provisioning an E2B sandbox took longer than {constants.PROVISION_TIMEOUT_SECONDS} seconds."
                    ) from exc

                # Outside the provisioning bound: the claim is bound by now, so it can no longer
                # be mistaken for an abandoned one, and starting the Agent has a bound of its own.
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

            # 创建时设的存活期已被建沙箱、等 Agent 就绪花掉了一截，而 Agent 的空闲计时从它启动
            # 才开始算，所以这里从现在起再续一次，沙箱才不会先于 Agent 到期。
            await self._renew_sandbox(claim.record.sandbox_id)
            return handle

    async def extend_lifetime(self, conversation_id: str) -> None:
        """Renew the E2B deadline of the sandbox still serving this conversation.

        :param conversation_id: Conversation whose turn is running or just ended.
        """
        await self._lifetime.extend(conversation_id)

    async def _renew_sandbox(self, sandbox_id: str | None) -> None:
        """Set this sandbox to expire idle_timeout_seconds from now, best effort."""
        await self._lifetime.renew(sandbox_id)

    async def needs_replacement(self, conversation_id: str) -> bool:
        """Tell whether the sandbox serving a conversation is old enough to be replaced next turn.

        :param conversation_id: Conversation to look at.
        :return: Whether a started sandbox is recorded and has reached max_lifetime_seconds.
        """
        record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
        if record is None or not record.is_started:
            return False
        return self._lifetime.is_past(record)

    async def terminate(self, conversation_id: str) -> None:
        """Let the Agent push its workspace, then stop its sandbox, retaining the record.

        Takes about STOP_GRACE_SECONDS at most, plus the final kill request.

        :param conversation_id: Conversation whose sandbox should stop.
        :raises AgentProvisionError: If E2B could not stop the sandbox.
        """
        async with self._conversation_lock(conversation_id):
            record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
            if record is not None:
                await _SandboxClaim(record, self.config).terminate(reason="terminated")

    async def shutdown(self) -> None:
        """Stop all active sandboxes owned by this API service.

        :raises AgentProvisionError: If an active sandbox could not be stopped.
        """
        records = [record async for record in E2BSandboxRecord.objects.active()]
        for record in records:
            async with self._conversation_lock(record.conversation_id):
                # 不等 Agent 推送：沙箱是一个个停的，每个都等上 20 秒，停服就要等 N 倍。
                await _SandboxClaim(record, self.config).terminate(reason="terminated", graceful=False)

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
                # As the Agent's user; without it envd runs the command as its default user.
                await sandbox.commands.run("pwd", user=provider.config.agent_user)

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
            http_headers=agent_health.port_headers(sandbox),
            # Our self-hosted E2B port proxy rejects a forwarded host different from its
            # exposed-port host with HTTP 400 (`bad target`).
            send_forwarded_host=False,
        )

    async def _create_sandbox(self) -> AsyncSandbox:
        """Ask E2B for a sandbox from the configured template.

        :raises AgentProvisionError: If E2B refuses or fails to create one.
        """
        try:
            return await AsyncSandbox.create(
                self.config.template,
                timeout=self.config.idle_timeout_seconds,
                api_key=self.config.api_key,
                api_url=self.config.api_url,
                domain=self.config.domain,
            )
        except constants.SANDBOX_ERRORS as exc:
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
            # 与沙箱存活期是同一个秒数：空闲到点 Agent 退出，沙箱也在这一刻到期。
            idle_timeout_seconds=config.idle_timeout_seconds,
        )

    async def _keep_for_next_turn(
        self, claim: _SandboxClaim, sandbox: AsyncSandbox, handle: AgentRuntimeHandle
    ) -> bool:
        """Tell whether a running sandbox may serve the next turn, retiring it when it may not.

        :return: True to reuse it; False once it has been stopped and released.
        :raises AgentProvisionError: If E2B could not stop a sandbox that has to go.
        """
        health = await self._probe_reused_agent(claim, sandbox, handle)

        # 不可达：Agent 已空闲退出、崩溃，或进程还在却几次都不应答（卡死、端口代理坏了）。不在原
        # 沙箱里重新拉起，整个换掉。仍走优雅停止：进程已不在时信号立即失败返回，不耽误；进程还在
        # 的话，它能先把工作区推上去。
        if health is None:
            logger.warning(
                "The Agent in E2B sandbox %s of conversation %s does not answer /health; replacing the sandbox",
                claim.record.sandbox_id,
                claim.record.conversation_id,
            )
            await claim.retire(sandbox, reason="unhealthy")
            return False

        # 满 max_lifetime 才换，而且只在没有一轮在跑时换：进行中的对话（比如另一个标签页发起的）
        # 不能被打断。它在跑时这一轮随后会因 Runtime 忙被拒，年龄留到下一轮再看。
        # 已知窗口：running 读出来是 false 之后、SIGTERM 送到之前，另一个 worker 可能刚好让 Agent
        # 接下一轮，那一轮会被停掉（先推送再退出）。要堵死得由 Agent 提供与 RunGuard 互斥的「停止
        # 接新 run」，这里不做；它只在满 24 小时那一刻、且两个 worker 同时开一轮时才会发生。
        if self._lifetime.is_past(claim.record) and not health.running:
            logger.info(
                "E2B sandbox %s of conversation %s reached its maximum lifetime; replacing it",
                claim.record.sandbox_id,
                claim.record.conversation_id,
            )
            await claim.retire(sandbox, reason="recycled")
            return False

        return True

    async def _probe_reused_agent(
        self, claim: _SandboxClaim, sandbox: AsyncSandbox, handle: AgentRuntimeHandle
    ) -> RuntimeHealth | None:
        """Read a reused Agent's health, retrying only while its process is still there."""
        for attempt in range(constants.REUSE_HEALTH_ATTEMPTS):
            if attempt:
                # 进程已经不在（空闲退出或崩溃，最常见的情形）就不必再等，直接换沙箱。还在的话可能
                # 只是端口代理抖了一下，隔一会儿再探：紧接着重探多半撞上同一次抖动。
                if not await claim.is_agent_alive(sandbox):
                    return None
                await asyncio.sleep(constants.REUSE_HEALTH_RETRY_INTERVAL_SECONDS)

            if (health := await agent_health.read_agent_health(handle)) is not None:
                return health
        return None

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
