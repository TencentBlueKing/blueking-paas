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

from ag_ui.core import CustomEvent

from app_spark_agent import settings
from app_spark_agent.app_supervisor.app_spec import build_app_spec
from app_spark_agent.app_supervisor.process import (
    ManagedProcess,
    ProcessRegistry,
    http_get_answers,
    tcp_port_is_open,
)
from app_spark_agent.app_supervisor.types import (
    CRASH_RETRY_INTERVAL_SECONDS,
    CRASH_RETRY_LIMIT,
    CRASH_WATCH_POLL_SECONDS,
    DEFAULT_LAUNCH_LABEL,
    DEFAULT_LAUNCH_PATH,
    LAUNCH_EVENT_RUN_ID,
    LAUNCHED_EVENT_NAME,
    LISTEN_TIMEOUT_SECONDS,
    PORT_FREE_TIMEOUT_SECONDS,
    AppLaunchConflict,
    AppLaunchFailed,
    AppStatus,
    LaunchResult,
)
from app_spark_agent.state import AppendLog
from app_spark_agent.ui_events import persist_ui_events


class AppSupervisor:
    """Launch, restart, and watch the single workspace application process."""

    def __init__(self, workspace: Path, processes: ProcessRegistry, ui_events: AppendLog) -> None:
        # uvicorn 的 cwd，必须能 import 到应用的入口。
        self.workspace = workspace

        # 只落 app.launched，给控制面 drain；不往 /runs SSE 里插。
        self._ui_events = ui_events

        # 进程层只管 spawn / stop / poll / probe：启什么由这边每次 launch 构造 spec 交给它，
        # 怎么算就绪也由这边的探针决定。processes 把子进程挂到 SIGTERM / 空闲退出名单上。
        self._process = ManagedProcess(processes, probe=self._app_answers)

        # 与 RunGuard 分开：run 进行中仍允许 launch，第二次 launch 才冲突。
        self._lock = asyncio.Lock()
        self._status = AppStatus.NOT_STARTED

        # 从上次手动 launch 起算。成功也不清零，避免听上又立刻崩时无限重启。
        self._auto_restarts = 0

    @property
    def port(self) -> int:
        """Return the port the application is expected to listen on."""
        return settings.APP_PORT

    async def app_status(self) -> AppStatus:
        """Return not_started, unhealthy, or healthy from live listen state."""

        # 不做成 property：判定要发一次真请求，把网络 I/O 藏在属性读取后面会让调用方看不出代价。
        #
        # 从未 launch 过就保持 not_started，哪怕别人占着端口。
        if self._status == AppStatus.NOT_STARTED:
            return AppStatus.NOT_STARTED

        # 健康看实听，不看上次写入的 _status：进程可能刚掉。
        if await self._is_up():
            return AppStatus.HEALTHY
        return AppStatus.UNHEALTHY

    async def launch(self) -> LaunchResult:
        """Start or restart the application and persist app.launched when it listens."""

        # 不接受参数：路径和标签都是常量，见 DEFAULT_LAUNCH_PATH。
        #
        # 不排队：进行中的 launch 被第二次打到就冲突。
        if self._lock.locked():
            raise AppLaunchConflict("An application launch is already in progress.")

        async with self._lock:
            # 端口被占、却不是我们的子进程：不杀、不发事件。这里问 TCP 而不是就绪探针——
            # 占着端口的东西不一定说 HTTP，用 HTTP 探针会把它当成端口空着，接着 bind 失败。
            if self._port_is_taken() and not self._process.living():
                raise AppLaunchConflict("The application port is owned by a process this supervisor did not start.")

            # 已是监督器进程：再次 launch 一律先停再拉，好加载新代码。
            if self._process.living():
                self._process.stop()
                # 等的是端口真被放开，同样与「能不能应答」无关。
                await self._wait_until(lambda: not self._port_is_taken(), PORT_FREE_TIMEOUT_SECONDS)

            # 手动 launch 重新开始自动拉起额度。
            self._auto_restarts = 0
            await self._start_and_wait()
            result = await self._result()
            await self._emit_launched(result)
            return result

    async def watch(self) -> None:
        """Restart a dropped application up to CRASH_RETRY_LIMIT times, then leave it unhealthy."""
        while True:
            await asyncio.sleep(CRASH_WATCH_POLL_SECONDS)

            # 用户正在 launch，或从未拉起过：监督不插手。
            if self._lock.locked() or self._status == AppStatus.NOT_STARTED:
                continue

            # 子进程还在且端口实听，不必重启。
            if await self._is_up():
                continue

            # 额度用尽只标 unhealthy，等下一次手动 launch。
            if self._retries_exhausted():
                self._status = AppStatus.UNHEALTHY
                continue

            # 掉听后先等一段，避免进程刚退出就立刻拉起。
            await asyncio.sleep(CRASH_RETRY_INTERVAL_SECONDS)

            # 等待期间用户可能已经手动 launch，或应用自己又听上了。
            if self._lock.locked() or await self._is_up():
                continue

            if self._retries_exhausted():
                self._status = AppStatus.UNHEALTHY
                continue

            try:
                async with self._lock:
                    # 拿到锁后再看一眼：可能刚被另一轮 launch 拉起来。
                    if await self._is_up():
                        continue

                    if self._retries_exhausted():
                        self._status = AppStatus.UNHEALTHY
                        continue

                    # 计入本次自动拉起；成功也不清零，同一手动 launch 之后最多三次。
                    self._auto_restarts += 1
                    self._process.stop()
                    await self._start_and_wait()
                    await self._emit_launched(await self._result())
            except Exception:  # noqa: BLE001
                # AppLaunchFailed 之外，spawn / 写事件也可能抛。只捕前者会拆掉整条 watch。
                # 标 unhealthy 后继续转；额度未满下一轮还会再试。
                self._status = AppStatus.UNHEALTHY

    async def _app_answers(self) -> bool:
        """Probe the agreed port. This is the readiness the process layer is given."""

        # 发一次 GET 而不是只连 TCP：端口 bind 上到能处理请求之间那段窗口不能算就绪。
        # 状态码不看，4xx / 5xx 也算在听——应用返回什么是它自己的事。
        return await http_get_answers(self.port)

    def _port_is_taken(self) -> bool:
        """Return whether anything at all holds the agreed port, HTTP or not."""
        return tcp_port_is_open(self.port)

    async def _is_up(self) -> bool:
        """Return whether the supervisor child is alive and the port answers the readiness probe."""
        return self._process.living() and await self._process.is_ready()

    def _retries_exhausted(self) -> bool:
        """Return whether automatic restarts since the last manual launch are used up."""
        return self._auto_restarts >= CRASH_RETRY_LIMIT

    async def _result(self) -> LaunchResult:
        # app.launched 用这一份四要素。不含 url：能打开的地址由控制面签发，沙箱这边不知道。
        return LaunchResult(
            port=self.port,
            path=DEFAULT_LAUNCH_PATH,
            label=DEFAULT_LAUNCH_LABEL,
            app_status=await self.app_status(),
        )

    async def _emit_launched(self, result: LaunchResult) -> None:
        # 只落盘，不往进行中的 /runs SSE 里插 CUSTOM。
        event = CustomEvent(
            name=LAUNCHED_EVENT_NAME,
            value={
                "port": result.port,
                "path": result.path,
                "label": result.label,
                "app_status": result.app_status,
            },
        )
        await persist_ui_events([event], log=self._ui_events, run_id=LAUNCH_EVENT_RUN_ID)

    async def _start_and_wait(self) -> None:
        """Spawn the child and wait until the port listens, or fail the launch."""

        # 每次重新构造 spec：两次 launch 之间端口和环境都可能已经变了。
        self._process.start(build_app_spec(self.workspace, self.port))
        deadline = time.monotonic() + LISTEN_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            # 进程先死了就不必再空等超时。
            if not self._process.living():
                self._status = AppStatus.UNHEALTHY
                raise AppLaunchFailed("The application process exited before it listened.")

            if await self._process.is_ready():
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
