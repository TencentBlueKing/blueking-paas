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

"""The one workspace child the supervisor starts, stops, and checks for a listen."""

import os
import signal
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import IO, Protocol

from app_spark_agent import settings
from app_spark_agent.app_supervisor.types import APP_PORT_ENV, SECRET_ENV_KEYS, STOP_TIMEOUT_SECONDS


class ProcessRegistry(Protocol):
    """Where a spawned child is recorded so SIGTERM can stop it."""

    def register(self, process: subprocess.Popen[bytes]) -> None: ...


class ProcessSpawn(Protocol):
    """Start one application child. Tests inject a fake."""

    def __call__(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        stdout: int | IO[bytes],
        stderr: int,
        start_new_session: bool,
    ) -> subprocess.Popen[bytes]: ...


class AppProcess:
    """Spawn, stop, and probe the workspace application process."""

    def __init__(
        self,
        workspace: Path,
        processes: ProcessRegistry,
        *,
        connect: Callable[[], bool] | None = None,
        spawn: ProcessSpawn | None = None,
    ) -> None:
        self.workspace = workspace
        self._processes = processes
        self._connect = connect or self.port_is_open
        self._spawn = spawn or _spawn_popen
        self._child: subprocess.Popen[bytes] | None = None

    @property
    def port(self) -> int:
        """Return the port the application is expected to listen on."""
        return settings.APP_PORT

    def living(self) -> bool:
        """Return whether the supervisor still has a running child."""
        return self._child is not None and self._child.poll() is None

    def is_listening(self) -> bool:
        """Return whether the agreed port accepts a TCP connection."""
        return self._connect()

    def port_is_open(self) -> bool:
        """Probe 127.0.0.1 on the agreed port."""
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                return True
        except OSError:
            return False

    def build_child_environ(self, source: dict[str, str] | None = None) -> dict[str, str]:
        """Copy the parent environment, inject the app port, and drop secrets."""
        env = dict(os.environ if source is None else source)
        for key in SECRET_ENV_KEYS:
            env.pop(key, None)
        env[APP_PORT_ENV] = str(self.port)
        return env

    def start_argv(self) -> list[str]:
        """Return the command that starts main:app on the agreed port."""
        return [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(self.port),
        ]

    def start(self) -> None:
        """Spawn the child, attach its output to the app log, and register it."""
        log_file = _open_app_log()
        try:
            self._child = self._spawn(
                self.start_argv(),
                cwd=self.workspace,
                env=self.build_child_environ(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        finally:
            if not isinstance(log_file, int):
                log_file.close()
        self._processes.register(self._child)

    def stop(self) -> None:
        """SIGTERM the current child, then SIGKILL if it is still alive."""
        process = self._child
        self._child = None
        if process is None or process.poll() is not None:
            return
        _stop_process(process)


def _open_app_log() -> int | IO[bytes]:
    """Open the application log for append, or discard output when that file cannot be used."""
    try:
        return open(settings.APP_LOG_PATH, "ab")
    except OSError:
        return subprocess.DEVNULL


# 单独抽出默认 spawn：测试注入假进程，不必去补丁 subprocess.Popen。
def _spawn_popen(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout: int | IO[bytes],
    stderr: int,
    start_new_session: bool,
) -> subprocess.Popen[bytes]:
    """Start one application child with Popen."""
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
