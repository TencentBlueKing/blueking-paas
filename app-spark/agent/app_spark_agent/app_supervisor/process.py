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

import os
import signal
import socket
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Protocol

# SIGTERM 之后等多久再 SIGKILL。
STOP_TIMEOUT_SECONDS = 5.0


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


class ManagedProcess:
    """Spawn, poll, probe, and stop the one child process a caller hosts."""

    def __init__(self, processes: ProcessRegistry, *, probe: Callable[[], bool]) -> None:
        # 每拉起一个子进程就登记，空闲退出 / SIGTERM 的 stop_all 才能杀到。
        self._processes = processes

        # 就绪由调用方定义：这一层不知道该连哪个端口，也不解析 HTTP。
        self._probe = probe
        self._child: subprocess.Popen[bytes] | None = None

    def living(self) -> bool:
        """Return whether the child this object started is still running."""
        return self._child is not None and self._child.poll() is None

    def is_ready(self) -> bool:
        """Return whether the caller's readiness probe passes.

        与 living 无关：探针可能被别人启的进程满足，判活要两者一起看。
        """
        return self._probe()

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
