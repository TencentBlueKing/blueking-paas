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

"""Agent Runtimes spawned as processes on this host.

For development and tests. Process handles live in memory only: nothing here survives a restart
of this service, and nothing tries to reclaim a Runtime it did not start.
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import os
import secrets
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx2

from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, LocalProcessConfig, StateCallback
from app_spark_api.agent.runtime.exceptions import AgentProvisionError, AgentWorkspaceBusyError
from app_spark_api.agent.runtime.providers.base import AgentRuntimeProvider
from app_spark_api.utils.urls import to_path_info

logger = logging.getLogger(__name__)

# The agent reads its whole configuration from variables under this prefix.
ENV_PREFIX = "APP_SPARK_AGENT_"

ASGI_TARGET = "app_spark_agent.server.asgi:app"

HEALTH_POLL_INTERVAL_SECONDS = 0.05
HEALTH_PROBE_TIMEOUT_SECONDS = 0.5

# How much of a failed Runtime's own log to quote back. A configuration error kills it during
# import, and its traceback is the only thing that can say why.
LOG_TAIL_LINES = 40

SHUTDOWN_GRACE_SECONDS = 10


@dataclass(frozen=True)
class _LocalRuntime:
    """One spawned Runtime and what is needed to police and stop it."""

    handle: AgentRuntimeHandle
    process: subprocess.Popen[bytes]
    workspace_dir: Path
    log_path: Path

    @property
    def alive(self) -> bool:
        """Whether the process is still running."""
        return self.process.poll() is None


# Terminating children is the one cleanup that cannot be skipped, and a crashing worker will not
# run any async teardown, so this is a plain module-level list drained by `atexit`.
_spawned: list[subprocess.Popen[bytes]] = []


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop a Runtime process, escalating only if it refuses to go."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=SHUTDOWN_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@atexit.register
def _terminate_all() -> None:
    """Take every Runtime this process started down with it."""
    for process in _spawned:
        try:
            _terminate(process)
        except OSError:  # pragma: no cover - the process is already gone
            pass


class LocalProcessProvider(AgentRuntimeProvider):
    """Spawn each conversation's Agent Runtime as a uvicorn process on this host.

    :param config: Where the agent project lives and how its processes are configured.
    """

    def __init__(self, config: LocalProcessConfig) -> None:
        self.config = config
        self._runtimes: dict[str, _LocalRuntime] = {}
        # Two requests for the same new conversation would otherwise both see "no Runtime" and
        # each spawn one, leaving an orphan nobody can reach or stop.
        self._lock = asyncio.Lock()

    def workspace_dir(self, project_id: str) -> Path:
        """Return the directory the Project's agents work in.

        Derived rather than recorded: as long as provisioning is deterministic there is nothing
        to remember, and a lookup table would only be another thing that can disagree with
        reality.
        """
        return Path(self.config.workspace_root) / project_id

    def state_dir(self, conversation_id: str) -> Path:
        """Return the directory a conversation's durable state is kept in.

        Rooted outside :meth:`workspace_dir` on purpose: the agent's own file tools are scoped
        to the workspace, so state kept inside it would be something the agent could destroy.
        """
        return Path(self.config.state_root) / conversation_id

    async def ensure(
        self,
        *,
        project_id: str,
        conversation_id: str,
        state_callback: StateCallback | None = None,
    ) -> AgentRuntimeHandle:
        async with self._lock:
            existing = self._runtimes.get(conversation_id)
            if existing is not None:
                if existing.alive:
                    return existing.handle
                # The process died on its own; forget it so a new one can take its place.
                logger.warning(
                    "Agent Runtime for conversation %s exited on its own:\n%s",
                    conversation_id,
                    _tail(existing.log_path),
                )
                self._forget(conversation_id)

            workspace_dir = self.workspace_dir(project_id)
            self._reject_workspace_conflict(conversation_id, workspace_dir)
            runtime = await self._spawn(
                conversation_id=conversation_id,
                workspace_dir=workspace_dir,
                state_dir=self.state_dir(conversation_id),
                state_callback=state_callback,
            )
            self._runtimes[conversation_id] = runtime
            return runtime.handle

    async def peek(self, conversation_id: str) -> AgentRuntimeHandle | None:
        async with self._lock:
            runtime = self._runtimes.get(conversation_id)
            # A dead process is deliberately not forgotten here: cleaning up is `ensure`'s job,
            # and it wants the log of the corpse to explain why it had to start a replacement.
            if runtime is None or not runtime.alive:
                return None
            return runtime.handle

    async def terminate(self, conversation_id: str) -> None:
        async with self._lock:
            runtime = self._runtimes.get(conversation_id)
            if runtime is None:
                return
            _terminate(runtime.process)
            self._forget(conversation_id)

    async def shutdown(self) -> None:
        async with self._lock:
            for conversation_id in list(self._runtimes):
                _terminate(self._runtimes[conversation_id].process)
                self._forget(conversation_id)

    def _forget(self, conversation_id: str) -> None:
        """Drop a Runtime from both the per-conversation map and the shutdown list."""
        runtime = self._runtimes.pop(conversation_id, None)
        if runtime is not None and runtime.process in _spawned:
            _spawned.remove(runtime.process)

    def _reject_workspace_conflict(self, conversation_id: str, workspace_dir: Path) -> None:
        """Refuse a second live Runtime on one workspace.

        A workspace belongs to a Project but a Runtime belongs to a conversation, so without
        this two conversations of the same Project would edit the same files at once.
        """
        for other_id, runtime in list(self._runtimes.items()):
            if other_id == conversation_id or not runtime.alive:
                continue
            if runtime.workspace_dir == workspace_dir:
                raise AgentWorkspaceBusyError(f"Conversation {other_id} already has a running Agent on this project.")

    async def _spawn(
        self,
        *,
        conversation_id: str,
        workspace_dir: Path,
        state_dir: Path,
        state_callback: StateCallback | None,
    ) -> _LocalRuntime:
        """Start one Runtime and return it once it answers ``/health``."""
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        log_path = state_dir.parent / f"{state_dir.name}-uvicorn.log"
        runtime_token = secrets.token_urlsafe(32)

        # Creating directories and forking a process both block, and this runs inside a request
        # handler -- so they happen on a worker thread rather than on the event loop.
        process = await asyncio.to_thread(
            self._start_process,
            port=port,
            workspace_dir=workspace_dir,
            state_dir=state_dir,
            log_path=log_path,
            runtime_token=runtime_token,
            state_callback=state_callback,
        )

        _spawned.append(process)
        try:
            await self._wait_until_healthy(base_url, process, log_path, runtime_token)
        except BaseException:
            _terminate(process)
            if process in _spawned:
                _spawned.remove(process)
            raise

        logger.info("Agent Runtime for conversation %s is serving on %s", conversation_id, base_url)
        return _LocalRuntime(
            handle=AgentRuntimeHandle(
                conversation_id=conversation_id,
                base_url=base_url,
                runtime_token=runtime_token,
            ),
            process=process,
            workspace_dir=workspace_dir,
            log_path=log_path,
        )

    def _start_process(
        self,
        *,
        port: int,
        workspace_dir: Path,
        state_dir: Path,
        log_path: Path,
        runtime_token: str,
        state_callback: StateCallback | None,
    ) -> subprocess.Popen[bytes]:
        """Prepare the directories and fork the Runtime.

        Blocking throughout; :meth:`_spawn` calls it on a worker thread.

        :raises AgentProvisionError: If ``uv`` is missing or the process cannot be started.
        """
        # Resolved rather than left to PATH lookup at exec time, so a missing `uv` is reported
        # as the setup problem it is instead of as a Runtime that never became healthy.
        uv = shutil.which("uv")
        if uv is None:
            raise AgentProvisionError(
                "`uv` was not found on PATH, and the local provider starts Agent Runtimes with it."
            )

        workspace_dir.mkdir(parents=True, exist_ok=True)
        state_dir.parent.mkdir(parents=True, exist_ok=True)

        # A pipe nobody drains blocks the server once it fills, and nothing reads this while the
        # Runtime is up -- it exists to explain a Runtime that died.
        with log_path.open("wb") as log_handle:
            try:
                return subprocess.Popen(
                    [
                        uv,
                        "run",
                        "--project",
                        self.config.agent_project_dir,
                        # Resolving dependencies is not something a request path should do, let
                        # alone reach the network for. The agent project must be synced already.
                        "--no-sync",
                        "uvicorn",
                        ASGI_TARGET,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                    ],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=self._build_env(
                        workspace_dir=workspace_dir,
                        state_dir=state_dir,
                        runtime_token=runtime_token,
                        state_callback=state_callback,
                    ),
                )
            except OSError as exc:
                raise AgentProvisionError(f"Could not spawn an Agent Runtime: {exc}") from exc

    def _build_env(
        self,
        *,
        workspace_dir: Path,
        state_dir: Path,
        runtime_token: str,
        state_callback: StateCallback | None,
    ) -> dict[str, str]:
        """Build the child's environment from this service's own plus the agent's settings."""
        # Provider-owned values are applied after `extra_env`: callers may extend the Runtime's
        # environment, but cannot accidentally replace its identity, state paths, or Bearer.
        env = {
            **os.environ,
            **self.config.extra_env,
            f"{ENV_PREFIX}WORKSPACE": str(workspace_dir),
            f"{ENV_PREFIX}STATE_DIR": str(state_dir),
            f"{ENV_PREFIX}RUNTIME_TOKEN": runtime_token,
        }
        if state_callback is not None:
            # An address already scoped to one conversation, plus a token that authorizes only
            # that one. Deliberately all the Runtime learns: it replicates to a URL it was
            # handed, and never has to know what a conversation is or which one it is serving.
            # The callback path is public (it may include FORCE_SCRIPT_NAME). This provider
            # talks to uvicorn on loopback, so Ingress never sees the request and the prefix
            # must come off. A remote sandbox provider would keep it.
            env[f"{ENV_PREFIX}CONTROL_PLANE_URL"] = (
                f"{self.config.callback_base_url.rstrip('/')}{to_path_info(state_callback.path)}"
            )
            env[f"{ENV_PREFIX}CONTROL_PLANE_TOKEN"] = state_callback.token
        if self.config.model is not None:
            env[f"{ENV_PREFIX}MODEL"] = self.config.model
        if self.config.model_api_key is not None:
            env[f"{ENV_PREFIX}MODEL_API_KEY"] = self.config.model_api_key
        return env

    async def _wait_until_healthy(
        self,
        base_url: str,
        process: subprocess.Popen[bytes],
        log_path: Path,
        runtime_token: str,
    ) -> None:
        """Poll ``/health`` until the Runtime answers, or explain why it never will.

        The process is checked on every pass rather than only at the deadline: a bad
        configuration kills the server during import, and saying so at once beats spending the
        whole timeout polling something that already exited.
        """
        deadline = time.monotonic() + self.config.startup_timeout_seconds
        async with httpx2.AsyncClient(
            timeout=HEALTH_PROBE_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {runtime_token}"},
        ) as client:
            while True:
                try:
                    if (await client.get(f"{base_url}/health")).status_code == 200:
                        return
                except httpx2.HTTPError:
                    pass
                if process.poll() is not None:
                    raise AgentProvisionError(f"The Agent Runtime exited during startup:\n{_tail(log_path)}")
                if time.monotonic() >= deadline:
                    raise AgentProvisionError(f"The Agent Runtime never became healthy:\n{_tail(log_path)}")
                await asyncio.sleep(HEALTH_POLL_INTERVAL_SECONDS)


def _free_port() -> int:
    """Reserve a loopback port and hand it back, so the server can be told where to listen.

    uvicorn is told its port rather than asked for one, because the only way to learn a port it
    chose itself would be to parse its log. That leaves a window in which something else could
    take the port; on a single host running its own agents, losing that race is not worth
    guarding against.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _tail(log_path: Path, lines: int = LOG_TAIL_LINES) -> str:
    """Return the end of a Runtime's own log, for a failure that has to be explained."""
    if not log_path.exists():
        return "(the Agent Runtime wrote no log)"
    return "\n".join(log_path.read_text(errors="replace").splitlines()[-lines:])
