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
import logging
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
    DevServerStatus,
    LaunchResult,
)
from app_spark_agent.state import AppendLog
from app_spark_agent.ui_events import persist_ui_events

logger = logging.getLogger(__name__)


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

        # 唯一需要记住的一位：其余三档都由「进程还在吗」加「端口应答吗」当场算出来，存一份缓存
        # 只会和实况不一致。not_started 算不出来，因为端口空着既可能是没拉过也可能是崩了。
        self._launched = False

        # 从上次手动 launch 起算。成功也不清零，避免起来又立刻崩时无限重启。
        self._auto_restarts = 0

    @property
    def port(self) -> int:
        """Return the port the application is expected to listen on."""
        return settings.APP_PORT

    async def dev_server_status(self) -> DevServerStatus:
        """Return not_started, stopped, starting, or ready from the live process and probe."""

        # 不做成 property：判定要发一次真请求，把网络 I/O 藏在属性读取后面会让调用方看不出代价。
        #
        # 从未 launch 过就保持 not_started，哪怕别人占着端口。
        if not self._launched:
            return DevServerStatus.NOT_STARTED

        # 先判活再判就绪，顺序就是这两档的区别所在：进程没了要重拉，进程在只是还答不出要等。
        if not self._process.living():
            return DevServerStatus.STOPPED

        return DevServerStatus.READY if await self._process.is_ready() else DevServerStatus.STARTING

    async def launch(self) -> LaunchResult:
        """Start or restart the application, waiting a bounded time for it to answer."""

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
        """Restart the application when its process dies, up to CRASH_RETRY_LIMIT times."""
        while True:
            await asyncio.sleep(CRASH_WATCH_POLL_SECONDS)

            # 用户正在 launch，或从未拉起过：监督不插手。
            if self._lock.locked() or not self._launched:
                continue

            # 判活，不判就绪。答不出 HTTP 的活进程只是 starting：可能在跑启动钩子、在编译模板，
            # 也可能首屏本来就慢过探针那 2 秒的读预算。停掉重拉既救不了它，还会打断一个正在
            # 预热的应用，把「慢」变成「永远起不来」。
            if self._process.living():
                continue

            # 额度用尽就不再拉，等下一次手动 launch。不必记状态，进程不在自然就是 stopped。
            if self._retries_exhausted():
                continue

            # 进程刚退出，先等一段再拉，避免崩溃循环被按轮询间隔的速度复现一遍。
            await asyncio.sleep(CRASH_RETRY_INTERVAL_SECONDS)

            # 等待期间用户可能已经手动 launch。
            if self._lock.locked() or self._process.living():
                continue

            try:
                async with self._lock:
                    # 拿到锁后再看一眼：可能刚被另一轮 launch 拉起来。
                    if self._process.living():
                        continue

                    if self._retries_exhausted():
                        continue

                    # 计入本次自动拉起；成功也不清零，同一手动 launch 之后最多三次。
                    self._auto_restarts += 1
                    self._process.stop()
                    await self._start_and_wait()
                    await self._emit_launched(await self._result())
            except Exception:
                # AppLaunchFailed 之外，spawn / 写事件也可能抛。只捕前者会拆掉整条 watch。
                # 这里是真把错误吞掉的地方，所以打一条日志；额度未满下一轮还会再试。
                logger.warning("Automatic restart %s failed", self._auto_restarts, exc_info=True)

    async def _app_answers(self) -> bool:
        """Probe the agreed port. This is the readiness the process layer is given."""

        # 发一次 GET 而不是只连 TCP：端口 bind 上到能处理请求之间那段窗口不能算就绪。
        # 状态码不看，4xx / 5xx 也算在听——应用返回什么是它自己的事。
        return await http_get_answers(self.port)

    def _port_is_taken(self) -> bool:
        """Return whether anything at all holds the agreed port, HTTP or not."""
        return tcp_port_is_open(self.port)

    def _retries_exhausted(self) -> bool:
        """Return whether automatic restarts since the last manual launch are used up."""
        return self._auto_restarts >= CRASH_RETRY_LIMIT

    async def _result(self) -> LaunchResult:
        # app.launched 用这一份四要素。不含 url：能打开的地址由控制面签发，沙箱这边不知道。
        return LaunchResult(
            port=self.port,
            path=DEFAULT_LAUNCH_PATH,
            label=DEFAULT_LAUNCH_LABEL,
            dev_server_status=await self.dev_server_status(),
        )

    async def _emit_launched(self, result: LaunchResult) -> None:
        # 只落盘，不往进行中的 /runs SSE 里插 CUSTOM。
        event = CustomEvent(
            name=LAUNCHED_EVENT_NAME,
            value={
                "port": result.port,
                "path": result.path,
                "label": result.label,
                "dev_server_status": result.dev_server_status,
            },
        )
        await persist_ui_events([event], log=self._ui_events, run_id=LAUNCH_EVENT_RUN_ID)

    async def _start_and_wait(self) -> None:
        """Spawn the child and wait until it answers, or fail if it exits first."""

        # 每次重新构造 spec：两次 launch 之间端口和环境都可能已经变了。
        self._process.start(build_app_spec(self.workspace, self.port))

        # spawn 成功就算 launch 过。not_started 从此不再回来：之后端口空着的意思是崩了，不是
        # 没拉过，而这两者的处置不同。
        self._launched = True

        deadline = time.monotonic() + LISTEN_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            # 进程退出是 launch 唯一算失败的情形：没有进程就没什么可等的了，模型该去读日志。
            if not self._process.living():
                raise AppLaunchFailed("The application process exited before it listened.")

            if await self._process.is_ready():
                return
            await asyncio.sleep(0.05)

        # 到点还没应答，但进程活着。不停它、也不抛：把慢启动杀掉正是「拿就绪当健康」的那个错。
        # 调用方从结果里的 starting 知道现在还打不开，watch 会继续照看这个进程。

    async def _wait_until(self, predicate: Callable[[], bool], seconds: float) -> None:
        # 重启前等旧端口放开，避免立刻 bind 失败。到期没等到就继续，由后面的实听等待收场。
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.05)
