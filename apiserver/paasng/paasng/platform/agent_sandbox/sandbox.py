# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import base64
import logging
import os
import re
import shlex
import time
import uuid

from kubernetes.client import CoreV1Api
from kubernetes.client.exceptions import ApiException
from kubernetes.stream import stream as kube_stream

from paas_wl.bk_app.agent_sandbox.constants import DEFAULT_IMAGE, DEFAULT_WORKDIR
from paas_wl.bk_app.agent_sandbox.exceptions import KresAgentSandboxError
from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp, agent_sandbox_kmodel
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.entities import CodeRunResult, ExecResult
from paasng.platform.agent_sandbox.exceptions import (
    SandboxCreateTimeout,
    SandboxError,
    SandboxExecTimeout,
    SandboxFileError,
)
from paasng.platform.agent_sandbox.fs import SandboxFS
from paasng.platform.agent_sandbox.process import SandboxProcess
from paasng.platform.applications.models import Application

# A special marker string to indicate the exit code in the stderr output.
# Explained: a echo command with this marker is appended to the end of the executed command.
_EXIT_CODE_MARKER = "__BKPAAS_EXIT_CODE__:"
_ENV_VAR_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

logger = logging.getLogger(__name__)


class AgentSandboxFactory:
    """A factory for creating agent sandboxes."""

    # The timeout for creating a sandbox, in seconds
    create_timeout = 30

    def __init__(self, app: Application):
        self.app = app
        self.kres_app = AgentSandboxKresApp(paas_app_id=app.code, tenant_id=app.tenant_id)

    def create(self) -> "KubernetesPodSandbox":
        """Create a new sandbox.

        :return: The sandbox object.
        """
        sandbox_id = str(uuid.uuid4())
        sandbox = AgentSandbox.create(
            self.kres_app,
            sandbox_id=sandbox_id,
            workdir=DEFAULT_WORKDIR,
            image=DEFAULT_IMAGE,
        )
        sandbox_created = False
        try:
            with self.kres_app.get_kube_api_client() as client:
                NamespacesHandler(client).ensure_namespace(self.kres_app.namespace)

            agent_sandbox_kmodel.create(sandbox)
            sandbox_created = True
            self._wait_for_running(sandbox.name)
        except ReadTargetStatusTimeout as exc:
            self._cleanup_sandbox_on_create_error(sandbox.name, sandbox_created)
            raise SandboxCreateTimeout(str(exc)) from exc
        except ApiException as exc:
            self._cleanup_sandbox_on_create_error(sandbox.name, sandbox_created)
            raise SandboxError("failed to create sandbox pod") from KresAgentSandboxError(str(exc), exc)
        return KubernetesPodSandbox(self.app, sandbox)

    def destroy(self, sbx: "KubernetesPodSandbox") -> None:
        try:
            agent_sandbox_kmodel.delete_by_name(self.kres_app, sbx.entity.name, non_grace_period=True)
        except ApiException as exc:
            raise SandboxError("failed to delete sandbox pod") from KresAgentSandboxError(str(exc), exc)

    def _wait_for_running(self, pod_name: str) -> None:
        with self.kres_app.get_kube_api_client() as client:
            kres.KPod(client).wait_for_status(
                name=pod_name,
                target_statuses={PodPhase.RUNNING.value},
                namespace=self.kres_app.namespace,
                timeout=self.create_timeout,
            )

    def _cleanup_sandbox_on_create_error(self, pod_name: str, sandbox_created: bool) -> None:
        if not sandbox_created:
            return

        try:
            agent_sandbox_kmodel.delete_by_name(self.kres_app, pod_name, non_grace_period=True)
        except (ApiException, AppEntityNotFound):
            logger.warning(
                "failed to cleanup sandbox pod after create error, pod_name=%s, namespace=%s",
                pod_name,
                self.kres_app.namespace,
                exc_info=True,
            )


class KubernetesPodSandbox(SandboxProcess, SandboxFS):
    """Sandbox implementation backed by a Kubernetes Pod.

    **Experimental only**

    """

    def __init__(self, app: Application, entity: AgentSandbox):
        self.app = app
        self.entity = entity
        self.kres_app = self.entity.app
        self.namespace = self.kres_app.namespace

    def exec(
        self, cmd: list[str] | str, cwd: str | None = None, env: dict | None = None, timeout: int = 60
    ) -> ExecResult:
        """Execute a command inside the sandbox.

        :param cmd: The command to execute, can be a string or a list of strings.
        :param cwd: The working directory, defaults to the sandbox's workdir.
        :param env: The environment variables to set, defaults to empty.
        :param timeout: The timeout for the command execution, in seconds.
        """
        cwd = cwd or self.entity.workdir
        env = env or {}
        shell_cmd = self._build_shell_command(cmd, cwd, env)
        stdout, stderr = self._stream_exec(shell_cmd, timeout=timeout)
        stderr, exit_code = self._extract_exit_code(stderr)
        return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

    def code_run(self, content: str, language: str = "Python") -> CodeRunResult:
        """Run a piece of code inside the sandbox."""
        if language.lower() != "python":
            raise SandboxError(f"unsupported language: {language}")

        filename = os.path.join(self.entity.workdir, f"code_run_{self.entity.sandbox_id[:8]}.py")
        self.upload_file(content.encode(), filename)
        result = self.exec(["python", filename], cwd=self.entity.workdir)
        return CodeRunResult(stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code)

    def create_folder(self, path: str, mode: str) -> None:
        """Create a folder inside the sandbox."""
        cmd = f"mkdir -p {shlex.quote(path)} && chmod {shlex.quote(mode)} {shlex.quote(path)}"
        result = self.exec(cmd)
        if result.exit_code != 0:
            raise SandboxFileError(result.stderr or "failed to create folder")

    def upload_file(self, file: bytes, remote_path: str, timeout: int = 30 * 60) -> None:
        """Upload a file to the sandbox."""
        encoded = base64.b64encode(file).decode()
        encoded_len = len(encoded)
        shell_cmd = [
            "/bin/sh",
            "-c",
            # dd reads a fixed number of bytes, so the command can finish without closing stdin explicitly.
            f"dd bs=1 count={encoded_len} status=none | base64 -d > {shlex.quote(remote_path)}; "
            f"echo {_EXIT_CODE_MARKER}$? 1>&2",
        ]
        _, stderr = self._stream_exec(shell_cmd, timeout=timeout, stdin_data=encoded)
        stderr, exit_code = self._extract_exit_code(stderr)
        if exit_code != 0:
            raise SandboxFileError(stderr or "failed to upload file")

    def delete_file(self, path: str, recursive: bool = False) -> None:
        """Delete a file from the sandbox.

        :param path: The path of the file to delete.
        :param recursive: Must be True to delete directories recursively.
        """
        flag = "-rf" if recursive else "-f"
        result = self.exec(["rm", flag, path])
        if result.exit_code != 0:
            raise SandboxFileError(result.stderr or "failed to delete file")

    def download_file(self, remote_path: str, timeout: int = 30 * 60) -> bytes:
        """Download a file from the sandbox."""
        result = self.exec(f"base64 {shlex.quote(remote_path)}", timeout=timeout)
        if result.exit_code != 0:
            raise SandboxFileError(result.stderr or "failed to download file")
        payload = "".join(result.stdout.splitlines())
        try:
            return base64.b64decode(payload)
        except Exception as exc:
            raise SandboxFileError("failed to decode file content") from exc

    def get_status(self) -> str:
        """Get the current status of the sandbox."""
        try:
            sandbox = agent_sandbox_kmodel.get(self.kres_app, self.entity.name)
        except AppEntityNotFound as exc:
            raise SandboxError("sandbox not found") from exc
        else:
            return sandbox.status

    def get_logs(self, tail_lines: int | None = None, timestamps: bool = False) -> str:
        """Get the logs of the sandbox."""
        try:
            with self.kres_app.get_kube_api_client() as client:
                resp = kres.KPod(client).get_log(
                    name=self.entity.name,
                    namespace=self.namespace,
                    tail_lines=tail_lines,
                    timestamps=timestamps,
                )
            return resp.data.decode("utf-8", errors="replace")
        except ApiException as exc:
            raise SandboxError("failed to get sandbox logs") from KresAgentSandboxError(str(exc), exc)

    def _build_shell_command(self, cmd: list[str] | str, cwd: str, env: dict) -> list[str]:
        """Build the shell command to be executed inside the sandbox."""
        cmd_str = cmd if isinstance(cmd, str) else " ".join(shlex.quote(item) for item in cmd)
        env_prefix = " ".join(f"{self._validate_env_key(key)}={shlex.quote(str(value))}" for key, value in env.items())
        if env_prefix:
            cmd_str = f"export {env_prefix}; {cmd_str}"
        if cwd:
            cmd_str = f"cd {shlex.quote(cwd)} && {cmd_str}"
        cmd_str = f"{cmd_str}; echo {_EXIT_CODE_MARKER}$? 1>&2"
        return ["/bin/sh", "-c", cmd_str]

    @staticmethod
    def _validate_env_key(key: object) -> str:
        key_str = str(key)
        if not _ENV_VAR_KEY_PATTERN.fullmatch(key_str):
            raise SandboxError(f"invalid environment variable key: {key_str!r}")
        return key_str

    def _stream_exec(self, command: list[str], timeout: int, stdin_data: str | None = None) -> tuple[str, str]:
        """Execute a command inside the sandbox."""
        with self.kres_app.get_kube_api_client() as client:
            try:
                resp = kube_stream(
                    CoreV1Api(client).connect_get_namespaced_pod_exec,
                    self.entity.name,
                    self.kres_app.namespace,
                    command=command,
                    stderr=True,
                    stdin=stdin_data is not None,
                    stdout=True,
                    tty=False,
                    _preload_content=False,
                    _request_timeout=timeout,
                )
                if stdin_data is not None:
                    resp.write_stdin(stdin_data)
                    close_stdin = getattr(resp, "close_stdin", None)
                    if callable(close_stdin):
                        close_stdin()
                stdout, stderr = self._collect_stream_output(resp, timeout)
                resp.close()
            except ApiException as exc:
                raise SandboxError("pod exec failed") from KresAgentSandboxError(str(exc), exc)
            else:
                return stdout, stderr

    def _collect_stream_output(self, resp, timeout: int) -> tuple[str, str]:
        """Collect output from the stream response."""
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        deadline = time.monotonic() + timeout
        while resp.is_open():
            if time.monotonic() > deadline:
                resp.close()
                raise SandboxExecTimeout("command execution timed out")
            resp.update(timeout=1)
            while resp.peek_stdout():
                stdout_chunks.append(resp.read_stdout())
            while resp.peek_stderr():
                stderr_chunks.append(resp.read_stderr())
        return "".join(stdout_chunks), "".join(stderr_chunks)

    @staticmethod
    def _extract_exit_code(stderr: str) -> tuple[str, int]:
        """Extract the exit code from stderr output."""
        lines = stderr.splitlines()
        if not lines:
            return stderr, -1
        last_line = lines[-1]
        if not last_line.startswith(_EXIT_CODE_MARKER):
            return stderr, -1
        code_str = last_line[len(_EXIT_CODE_MARKER) :].strip()
        try:
            exit_code = int(code_str)
        except ValueError:
            exit_code = -1
        cleaned = "\n".join(lines[:-1])
        return cleaned, exit_code
