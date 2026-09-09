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

"""Coordinate one launch at a time and restart a dropped application."""

import asyncio
import time
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from ag_ui.core import CustomEvent

from app_spark_agent.app_supervisor.process import AppProcess, ProcessRegistry, ProcessSpawn
from app_spark_agent.app_supervisor.types import (
    CRASH_RETRY_INTERVAL_SECONDS,
    CRASH_RETRY_LIMIT,
    CRASH_WATCH_POLL_SECONDS,
    DEFAULT_LAUNCH_LABEL,
    DEFAULT_LAUNCH_PATH,
    LAUNCHED_EVENT_NAME,
    LISTEN_TIMEOUT_SECONDS,
    PORT_FREE_TIMEOUT_SECONDS,
    AppLaunchConflict,
    AppLaunchFailed,
    AppStatus,
    LaunchResult,
    build_preview_url,
    validate_launch_label,
    validate_launch_path,
)
from app_spark_agent.state import AppendLog
from app_spark_agent.ui_events import persist_ui_events


class AppSupervisor:
    """Launch, restart, and watch the single workspace application process."""

    def __init__(
        self,
        workspace: Path,
        processes: ProcessRegistry,
        ui_events: AppendLog,
        *,
        connect: Callable[[], bool] | None = None,
        spawn: ProcessSpawn | None = None,
        listen_timeout: float = LISTEN_TIMEOUT_SECONDS,
        crash_retry_delay: float = CRASH_RETRY_INTERVAL_SECONDS,
        crash_retry_limit: int = CRASH_RETRY_LIMIT,
        watch_poll: float = CRASH_WATCH_POLL_SECONDS,
    ) -> None:
        self.workspace = workspace
        self._ui_events = ui_events
        self._process = AppProcess(workspace, processes, connect=connect, spawn=spawn)
        self._listen_timeout = listen_timeout
        self._crash_retry_delay = crash_retry_delay
        self._crash_retry_limit = crash_retry_limit
        self._watch_poll = watch_poll
        # 与 RunGuard 分开：run 进行中仍允许 launch，第二次 launch 才 409。
        self._lock = asyncio.Lock()
        self._status = AppStatus.NOT_STARTED
        self._path = DEFAULT_LAUNCH_PATH
        self._label = DEFAULT_LAUNCH_LABEL

        # 从上次手动 launch 起算。成功也不清零，避免听上又立刻崩时无限重启。
        self._auto_restarts = 0

    @property
    def port(self) -> int:
        """Return the port the application is expected to listen on."""
        return self._process.port

    @property
    def app_status(self) -> AppStatus:
        """Return not_started, unhealthy, or healthy from live listen state."""

        # 从未 launch 过就保持 not_started，哪怕别人占着端口。
        if self._status == AppStatus.NOT_STARTED:
            return AppStatus.NOT_STARTED

        # 健康看实听，不看上次写入的 _status：进程可能刚掉。
        if self._is_up():
            return AppStatus.HEALTHY
        return AppStatus.UNHEALTHY

    def preview_url(self, path: str) -> str:
        """Join the preview base URL with path."""
        return build_preview_url(path)

    def build_child_environ(self, source: dict[str, str] | None = None) -> dict[str, str]:
        """Copy the parent environment, inject the app port, and drop secrets."""
        return self._process.build_child_environ(source)

    def start_argv(self) -> list[str]:
        """Return the command that starts main:app on the agreed port."""
        return self._process.start_argv()

    async def launch(self, path: str | None = None, label: str | None = None) -> LaunchResult:
        """Start or restart the application and persist app.launched when it listens."""

        # 不排队：进行中的 launch 被第二次打到就 409。
        if self._lock.locked():
            raise AppLaunchConflict("An application launch is already in progress.")

        async with self._lock:
            resolved_path = self._resolve_path(path)
            resolved_label = self._resolve_label(label)

            # 端口在听、却不是我们的子进程：不杀、不发事件。
            if self._process.is_listening() and not self._process.living():
                raise AppLaunchConflict("The application port is owned by a process this supervisor did not start.")

            # 已是监督器进程：再次 launch 一律先停再拉，好加载新代码。
            if self._process.living():
                self._process.stop()
                await self._wait_until(lambda: not self._process.is_listening(), PORT_FREE_TIMEOUT_SECONDS)

            self._path = resolved_path
            self._label = resolved_label

            # 手动 launch 重新开始自动拉起额度。
            self._auto_restarts = 0
            await self._start_and_wait()
            result = self._result()
            await self._emit_launched(result)
            return result

    async def watch(self) -> None:
        """Restart a dropped application up to crash_retry_limit times, then leave it unhealthy."""
        while True:
            await asyncio.sleep(self._watch_poll)

            # 用户正在 launch，或从未拉起过：监督不插手。
            if self._lock.locked() or self._status == AppStatus.NOT_STARTED:
                continue

            # 子进程还在且端口实听，不必重启。
            if self._is_up():
                continue

            # 额度用尽只标 unhealthy，等下一次手动 launch。
            if self._retries_exhausted():
                self._status = AppStatus.UNHEALTHY
                continue

            # 掉听后先等一段，避免进程刚退出就立刻拉起。
            await asyncio.sleep(self._crash_retry_delay)

            # 等待期间用户可能已经手动 launch，或应用自己又听上了。
            if self._lock.locked() or self._is_up():
                continue

            if self._retries_exhausted():
                self._status = AppStatus.UNHEALTHY
                continue

            try:
                async with self._lock:
                    # 拿到锁后再看一眼：可能刚被另一轮 launch 拉起来。
                    if self._is_up():
                        continue

                    if self._retries_exhausted():
                        self._status = AppStatus.UNHEALTHY
                        continue

                    # 计入本次自动拉起；成功也不清零，同一手动 launch 之后最多三次。
                    self._auto_restarts += 1
                    self._process.stop()
                    await self._start_and_wait()
                    await self._emit_launched(self._result())
            except AppLaunchFailed:
                # 这次没听上。次数未满则下一轮还会再试。
                self._status = AppStatus.UNHEALTHY

    def _is_up(self) -> bool:
        """Return whether the supervisor child is alive and the port accepts a connection."""
        return self._process.living() and self._process.is_listening()

    def _retries_exhausted(self) -> bool:
        """Return whether automatic restarts since the last manual launch are used up."""
        return self._auto_restarts >= self._crash_retry_limit

    def _resolve_path(self, path: str | None) -> str:
        # 请求没带 path 就沿用上次；第一次是缺省 /。
        if path is None:
            return self._path
        return validate_launch_path(path)

    def _resolve_label(self, label: str | None) -> str:
        # 与 path 相同：省略则沿用，第一次是 Preview。
        if label is None:
            return self._label
        return validate_launch_label(label)

    def _result(self) -> LaunchResult:
        # HTTP 响应和 app.launched 共用这一份四要素。
        return LaunchResult(
            port=self.port,
            path=self._path,
            label=self._label,
            url=self.preview_url(self._path),
            app_status=self.app_status,
        )

    async def _emit_launched(self, result: LaunchResult) -> None:
        # 只落盘，不往进行中的 /runs SSE 里插 CUSTOM。
        event = CustomEvent(
            name=LAUNCHED_EVENT_NAME,
            value={
                "port": result.port,
                "path": result.path,
                "label": result.label,
                "url": result.url,
            },
        )
        await persist_ui_events([event], log=self._ui_events, run_id=str(uuid4()))

    async def _start_and_wait(self) -> None:
        """Spawn the child and wait until the port listens, or fail the launch."""
        self._process.start()
        deadline = time.monotonic() + self._listen_timeout
        while time.monotonic() < deadline:
            # 进程先死了就不必再空等超时。
            if not self._process.living():
                self._status = AppStatus.UNHEALTHY
                raise AppLaunchFailed("The application process exited before it listened.")

            # 健康只认 TCP 实听，不看 HTTP 状态码。
            if self._process.is_listening():
                self._status = AppStatus.HEALTHY
                return
            await asyncio.sleep(0.05)

        # 超时把我们拉起的进程停掉，避免留下一个半活子进程。
        self._process.stop()
        self._status = AppStatus.UNHEALTHY
        raise AppLaunchFailed("The application did not listen before the deadline.")

    async def _wait_until(self, predicate: Callable[[], bool], seconds: float) -> None:
        # 重启前等旧端口放开，避免立刻 bind 失败。到期没等到就继续，由后面的实听等待收场。
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.05)
