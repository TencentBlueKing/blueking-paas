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
from e2b import AsyncSandbox, NotFoundException, SandboxException, TimeoutException
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
    RuntimeHealth,
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

# 创建沙箱并绑定到占位这一整步的上限。限的是整步而不是单个请求，因为 SDK 会重试被限流的请求；
# 只有整步有上限，才能把一个早已没人管的未绑定占位，和一个还在创建中的占位区分开。
PROVISION_TIMEOUT_SECONDS = 120

# 未绑定的占位超过这个时长，说明创建它的 worker 在半路死掉了。多出的余量用来覆盖限时步骤前后的
# 数据库写入，以及各 worker 之间的时钟偏差。
ABANDONED_CLAIM_SECONDS = PROVISION_TIMEOUT_SECONDS + 60

# 已绑定的占位，超过启动超时再加这个余量仍没记下 Agent 已启动，说明启动它的 worker 在半路死掉了。
# 余量用来覆盖打开命令事件流、读取失败日志，以及各 worker 之间的时钟偏差。
STARTUP_GRACE_MARGIN_SECONDS = 60

# 每次 /health 探测都要经过 E2B 端口代理，所以给的时间比回环地址上的探测长；整段等待仍受
# E2BConfig.startup_timeout_seconds 限制。
HEALTH_POLL_INTERVAL_SECONDS = 0.5
HEALTH_PROBE_TIMEOUT_SECONDS = 3.0

# Agent 启动失败时，回传它自己日志末尾的多少行。配置错误会让它在 import 阶段就退出，那段 traceback
# 是唯一能说明原因的东西。
LOG_TAIL_LINES = 40

# 复用沙箱时，Agent 进程还在却不应答 /health，按这个次数、这个间隔探测，仍不应答才判定它不可用。
# 经端口代理的一次探测可能只是偶发失败，而换掉沙箱要让用户多等一次冷启动，还可能掐掉另一个标签页
# 正在跑的一轮。
REUSE_HEALTH_ATTEMPTS = 3
REUSE_HEALTH_RETRY_INTERVAL_SECONDS = 1.0

# 结束会话最多花多久，重连、发信号、等 Agent 退出都算在内，只有最后那次 kill 另算。Agent 有序关停
# 最多要 1 秒断连接、8 秒推送加回写、5 秒停应用子进程（见 agent settings 里的
# SHUTDOWN_DRAIN_TIMEOUT_SECONDS），剩下的留给重连。
STOP_GRACE_SECONDS = 20

# 沙箱里的停止命令每隔多久看一次 Agent 退出了没有。
STOP_POLL_INTERVAL_SECONDS = 0.2

# 等完 Agent 之后那次 kill 请求的上限，让结束会话的耗时贴近 STOP_GRACE_SECONDS，而不是 SDK 默认的
# 60 秒请求超时。
KILL_REQUEST_TIMEOUT_SECONDS = 5.0

# 一次续期的上限，SDK 自带的重试也算在内。续期挡在一轮的开头和结尾，控制面卡住时，不限时就会让
# 这一轮跟着多等一分钟。
RENEW_TIMEOUT_SECONDS = 5.0


async def read_agent_health(
    handle: AgentRuntimeHandle, *, timeout_seconds: float = HEALTH_PROBE_TIMEOUT_SECONDS
) -> RuntimeHealth | None:
    """Read the Runtime's /health behind handle, or None if it does not answer.

    :param handle: Where the Runtime should be reachable.
    :param timeout_seconds: Upper bound on this one probe.
    :return: Its health snapshot, or None if it gave no usable one.
    """
    try:
        return await AgentRuntimeClient(handle, timeout_seconds=timeout_seconds).health()
    except AgentUnavailableError:
        return None


async def probe_agent_health(
    handle: AgentRuntimeHandle, *, timeout_seconds: float = HEALTH_PROBE_TIMEOUT_SECONDS
) -> bool:
    """Tell whether the Runtime behind ``handle`` answers ``/health`` yet.

    :param handle: Where the Runtime should be reachable.
    :param timeout_seconds: Upper bound on this one probe.
    :return: Whether it answered with a usable health snapshot.
    """
    return await read_agent_health(handle, timeout_seconds=timeout_seconds) is not None


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
        # The claim each conversation's last turn on this worker was served from. A turn's event
        # stream renews through it, because that stream runs on the worker whose ensure started
        # the turn, and must not query the database for as long as the turn runs. Entries are
        # dropped when this worker retires the sandbox; one another worker retired is renewed
        # in vain until this worker serves the conversation again, which is harmless.
        self._served: dict[str, _SandboxClaim] = {}

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
                    await claim.extend_lifetime()
                    self._served[conversation_id] = claim
                    return existing_handle
                self._served.pop(conversation_id, None)

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

            # 创建时设的存活期已被建沙箱、等 Agent 就绪花掉了一截，而 Agent 的空闲计时从它启动
            # 才开始算，所以这里从现在起再续一次，沙箱才不会先于 Agent 到期。
            await claim.extend_lifetime()
            self._served[conversation_id] = claim
            return handle

    async def extend_lifetime(self, conversation_id: str) -> None:
        """Renew the E2B deadline of the sandbox this worker served a conversation's turn from.

        :param conversation_id: Conversation whose turn is running or just ended.
        """
        # 本 worker 没为它开过一轮就没有可续的：可能本轮中途被结束了，沙箱已被收掉，等下一轮重建。
        if (claim := self._served.get(conversation_id)) is not None:
            await claim.extend_lifetime()

    async def needs_replacement(self, conversation_id: str) -> bool:
        """Tell whether the sandbox serving a conversation is old enough to be replaced next turn.

        :param conversation_id: Conversation to look at.
        :return: Whether a started sandbox is recorded and has reached max_lifetime_seconds.
        """
        record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
        if record is None or not record.is_started:
            return False
        return _SandboxClaim(record, self.config).is_past_max_lifetime()

    async def terminate(self, conversation_id: str) -> None:
        """Let the Agent push its workspace, then stop its sandbox, retaining the record.

        Takes about STOP_GRACE_SECONDS at most, plus the final kill request.

        :param conversation_id: Conversation whose sandbox should stop.
        :raises AgentProvisionError: If E2B could not stop the sandbox.
        """
        async with self._conversation_lock(conversation_id):
            self._served.pop(conversation_id, None)
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
                self._served.pop(record.conversation_id, None)
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
                timeout=self.config.sandbox_timeout_seconds,
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
            # 与沙箱存活期同出一个配置：Agent 空闲到点先推送再退出，沙箱晚它 60 秒到期。
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
        if claim.is_past_max_lifetime() and not health.running:
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
        for attempt in range(REUSE_HEALTH_ATTEMPTS):
            if attempt:
                # 进程已经不在（空闲退出或崩溃，最常见的情形）就不必再等，直接换沙箱。还在的话可能
                # 只是端口代理抖了一下，隔一会儿再探：紧接着重探多半撞上同一次抖动。
                if not await claim.is_agent_alive(sandbox):
                    return None
                await asyncio.sleep(REUSE_HEALTH_RETRY_INTERVAL_SECONDS)

            if (health := await read_agent_health(handle)) is not None:
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

    async def terminate(self, *, reason: str, graceful: bool = True) -> None:
        """Stop this claim's sandbox, preserving the record for history.

        :param reason: Why it is ending, kept on the row.
        :param graceful: Let the Agent push its workspace first, see stop_agent.
        """
        record = self.record
        if record.sandbox_id is None:
            # Nothing to stop yet, unless a bind landed after this record was read. Releasing
            # only while still unbound leaves that sandbox claimed, so the fall-through below
            # reconnects and stops it instead of forgetting it.
            if await self._release(reason, only_unbound=True):
                return
            await record.arefresh_from_db()
            if record.sandbox_id is None or record.active_conversation_id is None:
                return
        # A sandbox whose Agent is still starting is stopped all the same; the request starting
        # it then finds its claim released when it goes to record the Agent.
        # 重连也算进 STOP_GRACE_SECONDS：结束会话的请求要在这个时间内返回，重连用掉的从等 Agent 里扣。
        started = time.monotonic()
        try:
            async with asyncio.timeout(STOP_GRACE_SECONDS):
                sandbox = await self.connect(reconcile=True, require_started=False)
        except TimeoutError as exc:
            raise AgentProvisionError(
                f"E2B did not say within {STOP_GRACE_SECONDS} seconds whether sandbox {record.sandbox_id} still runs."
            ) from exc
        if sandbox is None:
            return

        grace = STOP_GRACE_SECONDS - (time.monotonic() - started)
        await self.retire(sandbox, reason=reason, graceful=graceful, grace_seconds=grace)

    async def retire(
        self, sandbox: AsyncSandbox, *, reason: str, graceful: bool = True, grace_seconds: float | None = None
    ) -> None:
        """Stop this claim's connected sandbox and release the claim.

        :param sandbox: The sandbox bound to this claim.
        :param reason: Why it is ending, kept on the row.
        :param graceful: Let the Agent push its workspace first, see stop_agent.
        :param grace_seconds: How long the Agent gets; STOP_GRACE_SECONDS when omitted.
        :raises AgentProvisionError: If E2B could not kill the sandbox.
        """
        try:
            if graceful:
                await self.stop_agent(
                    sandbox, grace_seconds=STOP_GRACE_SECONDS if grace_seconds is None else grace_seconds
                )
        finally:
            # 被取消也要走到这里：结束会话的请求在等 Agent 的那 20 秒里被断开时，不 kill、不释放，
            # 会话已经关了，没有谁会再来收拾，这条记录会一直占着 Project，直到沙箱自己到期。
            await self._kill(sandbox)
            await self._release(reason)

    async def _kill(self, sandbox: AsyncSandbox) -> None:
        """Kill the sandbox, treating one already gone as killed.

        :raises AgentProvisionError: If E2B refused or did not answer in time.
        """
        try:
            await sandbox.kill(request_timeout=KILL_REQUEST_TIMEOUT_SECONDS)
        except NotFoundException:
            pass
        except SandboxException as exc:
            raise AgentProvisionError(f"Could not stop E2B sandbox {self.record.sandbox_id}: {exc}") from exc

    async def stop_agent(self, sandbox: AsyncSandbox, *, grace_seconds: float) -> None:
        """Ask the Agent to push its workspace and exit, waiting at most grace_seconds.

        Best-effort: whatever happens, the caller kills the sandbox next.

        :param sandbox: The sandbox bound to this claim.
        :param grace_seconds: How long to wait for the Agent to exit.
        """
        record = self.record

        # 没有进程号说明 Agent 从没通过健康检查，手里没有哪一轮要推送，也没有可以发信号的对象。
        if record.agent_pid is None:
            return

        # 预算已被重连用光：不再发信号，直接交给调用方 kill，结束会话的请求不能因此超时。
        if grace_seconds <= 0:
            logger.warning(
                "No time was left to let the Agent in E2B sandbox %s push its workspace; killing it", record.sandbox_id
            )
            return

        # SDK 的 commands.kill 发的是 SIGKILL，Agent 来不及推送，所以在沙箱里自己发 SIGTERM。
        # kill 失败说明进程已不在（Agent 空闲退出或崩溃），直接成功返回；否则等它退出。
        # 进程号是 Agent 自己的（启动时用了 exec），它由 envd 回收，不会留成僵尸让 kill -0 一直成功。
        pid = record.agent_pid
        command = (
            f"kill -TERM {pid} 2>/dev/null || exit 0; "
            f"while kill -0 {pid} 2>/dev/null; do sleep {STOP_POLL_INTERVAL_SECONDS}; done"
        )
        try:
            # 两层限时：envd 的 timeout 让 SDK 到点不再等，asyncio.timeout 兜住连接本身卡住。沙箱里
            # 那段循环不会被它们停下，但调用方紧接着就 kill 沙箱。
            async with asyncio.timeout(grace_seconds):
                await sandbox.commands.run(command, timeout=grace_seconds)
        except TimeoutError, TimeoutException:
            logger.warning(
                "The Agent in E2B sandbox %s did not exit within %.1f seconds of SIGTERM; killing the sandbox, "
                "so changes it has not pushed yet are lost",
                record.sandbox_id,
                grace_seconds,
            )
        # 不只接 SandboxException：envd 连接层的错误 SDK 会原样抛出。哪种错都一样交给调用方 kill。
        except Exception:
            logger.warning(
                "Could not ask the Agent in E2B sandbox %s to exit; killing the sandbox, so changes it has not "
                "pushed yet are lost",
                record.sandbox_id,
                exc_info=True,
            )

    async def is_agent_alive(self, sandbox: AsyncSandbox) -> bool:
        """Ask envd whether the recorded Agent process still exists; an unanswered question counts as yes."""
        pid = self.record.agent_pid
        if pid is None:
            return False

        # 走 envd 而不是端口代理：/health 不应答时，要区分的正是「进程没了」和「代理这条路不通」。
        try:
            async with asyncio.timeout(HEALTH_PROBE_TIMEOUT_SECONDS):
                result = await sandbox.commands.run(
                    f"kill -0 {pid} 2>/dev/null && echo alive || echo gone", timeout=HEALTH_PROBE_TIMEOUT_SECONDS
                )
        # 问不到就当它还在：宁可多探一次 /health，也不因为 envd 一时连不上就拆掉一个活着的 Agent。
        except Exception:
            logger.info(
                "Could not ask E2B sandbox %s whether its Agent is alive", self.record.sandbox_id, exc_info=True
            )
            return True
        return result.stdout.strip() != "gone"

    async def extend_lifetime(self) -> None:
        """Set this claim's sandbox to expire sandbox_timeout_seconds from now, best effort."""
        record = self.record
        if record.sandbox_id is None:
            return

        # 续期失败只记告警：对话本身不受影响，最坏是沙箱按上一次的存活期提前到期、下一轮重建。
        # 限时：它挡在一轮的开头和结尾，控制面卡住时不能让这一轮跟着等上 SDK 默认的 60 秒。
        # 不只接 SandboxException：控制面的网络错误不一定被 SDK 包成它。
        try:
            async with asyncio.timeout(RENEW_TIMEOUT_SECONDS):
                await AsyncSandbox.set_timeout(
                    record.sandbox_id,
                    self.config.sandbox_timeout_seconds,
                    api_key=self.config.api_key,
                    api_url=self.config.api_url,
                    domain=self.config.domain,
                    request_timeout=RENEW_TIMEOUT_SECONDS,
                )
        except Exception:
            logger.warning("Could not extend the lifetime of E2B sandbox %s", record.sandbox_id, exc_info=True)

    def is_past_max_lifetime(self) -> bool:
        """Whether this claim was made at least max_lifetime_seconds ago."""
        deadline = self.record.created_at + timedelta(seconds=self.config.max_lifetime_seconds)
        return timezone.now() >= deadline

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
