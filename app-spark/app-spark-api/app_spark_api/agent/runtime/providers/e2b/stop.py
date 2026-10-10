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

"""Stop the Agent process inside a sandbox, then kill the sandbox."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from e2b import AsyncSandbox, NotFoundException, SandboxException, TimeoutException

from app_spark_api.agent.runtime.exceptions import AgentProvisionError

from . import constants

if TYPE_CHECKING:
    from app_spark_api.agent.runtime.models import E2BSandboxRecord

logger = logging.getLogger(__name__)


class SandboxAgentStop:
    """Ask a sandbox Agent to push its workspace, then destroy the sandbox.

    _SandboxClaim implements connect and _release. Stopping stays here so a claim's
    record bookkeeping and its in-sandbox process shutdown can be read separately.
    """

    record: E2BSandboxRecord

    async def connect(self, *, reconcile: bool, require_started: bool = True) -> AsyncSandbox | None:
        """Reconnect to this claim's sandbox. _SandboxClaim implements it."""
        raise NotImplementedError

    async def _release(self, reason: str, *, only_unbound: bool = False, only_unstarted: bool = False) -> bool:
        """Clear this claim's active IDs. _SandboxClaim implements it."""
        raise NotImplementedError

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
            async with asyncio.timeout(constants.STOP_GRACE_SECONDS):
                sandbox = await self.connect(reconcile=True, require_started=False)
        except TimeoutError as exc:
            raise AgentProvisionError(
                f"E2B did not say within {constants.STOP_GRACE_SECONDS} seconds whether sandbox {record.sandbox_id} still runs."
            ) from exc
        if sandbox is None:
            return

        grace = constants.STOP_GRACE_SECONDS - (time.monotonic() - started)
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
                    sandbox, grace_seconds=constants.STOP_GRACE_SECONDS if grace_seconds is None else grace_seconds
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
            await sandbox.kill(request_timeout=constants.KILL_REQUEST_TIMEOUT_SECONDS)
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
            f"while kill -0 {pid} 2>/dev/null; do sleep {constants.STOP_POLL_INTERVAL_SECONDS}; done"
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
            async with asyncio.timeout(constants.HEALTH_PROBE_TIMEOUT_SECONDS):
                result = await sandbox.commands.run(
                    f"kill -0 {pid} 2>/dev/null && echo alive || echo gone",
                    timeout=constants.HEALTH_PROBE_TIMEOUT_SECONDS,
                )
        # 问不到就当它还在：宁可多探一次 /health，也不因为 envd 一时连不上就拆掉一个活着的 Agent。
        except Exception:
            logger.info(
                "Could not ask E2B sandbox %s whether its Agent is alive", self.record.sandbox_id, exc_info=True
            )
            return True
        return result.stdout.strip() != "gone"
