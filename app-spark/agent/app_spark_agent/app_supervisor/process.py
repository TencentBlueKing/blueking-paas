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

"""Hosting for one child process: spawn it, poll it, probe it, stop its group.

这一层不认识 uvicorn、端口、密钥和预览地址。要启什么由调用方用 ProcessSpec 说清楚，
怎么算就绪由调用方给的探针决定。
"""

import asyncio
import os
import signal
import socket
import subprocess
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Protocol

# SIGTERM 之后等多久再 SIGKILL。
STOP_TIMEOUT_SECONDS = 5.0

# 连不上就是没听，本机 connect 要么立刻成功要么立刻 ECONNREFUSED，不需要给够时间。
PROBE_CONNECT_TIMEOUT_SECONDS = 0.2

# 等应答要宽得多。这一段是应用自己处理一个请求的时间，不是建连时间：首次请求触发 lazy import、
# 渲染一个稍大的模板、查一次库，几百毫秒很正常。给太紧会把一个正在正常服务的应用判成掉听，
# 然后被 watch 停掉重拉。
PROBE_READ_TIMEOUT_SECONDS = 2.0


class ProcessRegistry(Protocol):
    """Where a spawned child is recorded so SIGTERM can stop it."""

    def register(self, process: subprocess.Popen[bytes]) -> None: ...


@dataclass(frozen=True)
class ProcessSpec:
    """One child process to start. Built fresh per start, so a changed port takes effect.

    :param argv: Command to run; argv[0] is the executable.
    :param cwd: Working directory the command is resolved against.
    :param env: The child's entire environment; nothing is inherited on top of it.
    :param log_path: File the child's stdout and stderr are appended to.
    """

    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str]
    log_path: Path


def tcp_port_is_open(port: int, *, host: str = "127.0.0.1", timeout: float = 0.2) -> bool:
    """Return whether host:port accepts a TCP connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def http_get_answers(
    port: int,
    *,
    host: str = "127.0.0.1",
    connect_timeout: float = PROBE_CONNECT_TIMEOUT_SECONDS,
    read_timeout: float = PROBE_READ_TIMEOUT_SECONDS,
    path: str = "/",
) -> bool:
    """Return whether host:port answers a GET with something that parses as an HTTP response."""

    # 比只连 TCP 严一点：uvicorn 绑上端口到真能处理请求之间有一小段窗口，纯 TCP 探针在那段时间
    # 就已经算就绪，预览打开会撞上空响应。
    #
    # 用 asyncio 而不是 http.client：这个探针在事件循环上每 0.5 秒被调一次，同步实现会在应用变慢
    # 时（正好是最该探的时候）把整个循环连同进行中的 /runs SSE 一起堵住。
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), connect_timeout)
    except OSError, TimeoutError:
        return False

    try:
        # Connection: close 让应用那边自己收尾。探针只要状态行，不读 body——半途断开会在应用
        # 日志里留下一行异常，而那个日志是模型读 traceback 用的，不该被探针刷。
        writer.write(f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n".encode())
        await writer.drain()
        status_line = await asyncio.wait_for(reader.readline(), read_timeout)
    except OSError, TimeoutError:
        # 连接被拒、应答超时、对端说的不是 HTTP：都当作没听。
        return False
    finally:
        writer.close()
        # 对端可能已经走了。关连接没关干净不该让一次成功的探测变成失败。
        with suppress(OSError, TimeoutError):
            await asyncio.wait_for(writer.wait_closed(), connect_timeout)

    # 任何 HTTP 响应都算在听，包括 4xx / 5xx。应用返回什么状态码是它自己的事，这里只判断
    # 「有没有一个 HTTP 服务在这个端口上」。
    return status_line.startswith(b"HTTP/")


class ManagedProcess:
    """Spawn, poll, probe, and stop the one child process a caller hosts."""

    def __init__(self, processes: ProcessRegistry, *, probe: Callable[[], Awaitable[bool]]) -> None:
        # 每拉起一个子进程就登记，空闲退出 / SIGTERM 的 stop_all 才能杀到。
        self._processes = processes

        # 就绪由调用方定义：这一层不知道该连哪个端口，也不解析 HTTP。探针是 awaitable，因为它
        # 要发一次真请求，而这一切都跑在 agent 自己的事件循环上。
        self._probe = probe
        self._child: subprocess.Popen[bytes] | None = None

    def living(self) -> bool:
        """Return whether the child this object started is still running."""
        return self._child is not None and self._child.poll() is None

    async def is_ready(self) -> bool:
        """Return whether the caller's readiness probe passes.

        与 living 无关：探针可能被别人启的进程满足，判活要两者一起看。
        """
        return await self._probe()

    def start(self, spec: ProcessSpec) -> None:
        """Spawn the child spec describes, attach its output to the log, and register it."""
        log_file = _open_log(spec.log_path)
        try:
            self._child = _spawn_popen(
                list(spec.argv),
                cwd=spec.cwd,
                env=dict(spec.env),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                # 独立进程组：停的时候能把子进程自己拉起的那些一起清掉。
                start_new_session=True,
            )
        finally:
            if not isinstance(log_file, int):
                log_file.close()
        self._processes.register(self._child)

    def stop(self) -> None:
        """SIGTERM the current child's group, then SIGKILL if it is still alive."""
        process = self._child
        self._child = None
        if process is None or process.poll() is not None:
            return
        _stop_process(process)


def _open_log(path: Path) -> int | IO[bytes]:
    """Open path for append, or discard output when that file cannot be used."""
    try:
        return open(path, "ab")
    except OSError:
        return subprocess.DEVNULL


# 单独抽出 Popen：单测 mock 这一层，不必给 ManagedProcess 加 spawn 参数。
def _spawn_popen(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout: int | IO[bytes],
    stderr: int,
    start_new_session: bool,
) -> subprocess.Popen[bytes]:
    """Start one child with Popen."""
    return subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        start_new_session=start_new_session,
    )


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """SIGTERM the process group, then SIGKILL whoever is still alive."""
    if process.poll() is not None:
        return
    try:
        if process.pid:
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    except OSError:
        process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            if process.pid:
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            return
        except OSError:
            process.kill()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass
