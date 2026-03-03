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

import copy
import logging
import re
import shlex

from django.utils import timezone
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.agent_sandbox.constants import DAEMON_BIND_PORT, DEFAULT_IMAGE
from paas_wl.bk_app.agent_sandbox.exceptions import KresAgentSandboxError
from paas_wl.bk_app.agent_sandbox.kres_entities import (
    AgentSandbox,
    AgentSandboxKresApp,
    AgentSandboxService,
    agent_sandbox_kmodel,
    agent_sandbox_svc_kmodel,
)
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.daemon_client import SandboxDaemonClient
from paasng.platform.agent_sandbox.entities import CodeRunResult, ExecResult
from paasng.platform.agent_sandbox.exceptions import (
    SandboxCreateTimeout,
    SandboxDaemonAPIError,
    SandboxError,
    SandboxExecError,
    SandboxFileError,
)
from paasng.platform.agent_sandbox.fs import SandboxFS
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.process import SandboxProcess
from paasng.platform.applications.models import Application

logger = logging.getLogger(__name__)


ENV_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def create_sandbox(
    application: Application,
    creator: str,
    name: str | None = None,
    env_vars: dict | None = None,
    snapshot: str | None = None,
    snapshot_entrypoint: list | None = None,
    workspace: str | None = None,
) -> Sandbox:
    """Create an agent sandbox record and its corresponding resources.

    :param application: The application that the sandbox belongs to.
    :param creator: The creator of the sandbox.
    :param name: The name of the sandbox, optional.
    :param env_vars: The environment variables dict, optional.
    :param snapshot: The snapshot name, optional.
    :param snapshot_entrypoint: The snapshot entrypoint command list, optional.
    :param workspace: The workspace path, optional.
    """
    sandbox_obj = Sandbox.objects.new(
        application=application,
        name=name,
        snapshot=snapshot or DEFAULT_IMAGE,
        snapshot_entrypoint=snapshot_entrypoint,
        env_vars=env_vars,
        creator=creator,
        workspace=workspace,
    )

    mgr = AgentSandboxResManager(application, sandbox_obj.target)
    try:
        mgr.provision(sandbox_obj)
    except SandboxError:
        sandbox_obj.status = SandboxStatus.ERR_CREATING.value
        sandbox_obj.save(update_fields=["status"])
        raise

    # The sandbox started successfully and running.
    sandbox_obj.status = SandboxStatus.RUNNING.value
    sandbox_obj.started_at = timezone.now()
    sandbox_obj.save(update_fields=["status", "started_at", "updated"])
    return sandbox_obj


def delete_sandbox(sandbox_obj: Sandbox) -> None:
    """Stop and delete a sandbox.

    :param sandbox_obj: The sandbox to delete.
    """
    mgr = AgentSandboxResManager(sandbox_obj.application, sandbox_obj.target)
    try:
        mgr.destroy_by_name(sandbox_obj.name)
    except SandboxError:
        sandbox_obj.status = SandboxStatus.ERR_DELETING.value
        sandbox_obj.save(update_fields=["status"])
        raise
    # TODO: delete the sandbox record?
    sandbox_obj.status = SandboxStatus.DELETED.value
    sandbox_obj.deleted_at = timezone.now()
    sandbox_obj.save(update_fields=["status", "deleted_at", "updated"])


def get_sandbox_client(sandbox_obj: Sandbox) -> "KubernetesPodSandbox":
    """Build a runtime sandbox client from a Sandbox record.

    :param sandbox_obj: The sandbox record.
    :returns: The runtime sandbox client for process and filesystem operations.
    """
    mgr = AgentSandboxResManager(sandbox_obj.application, sandbox_obj.target)
    return mgr.get_from_db_record(sandbox_obj)


class AgentSandboxResManager:
    """The class helps managing agent sandbox resources.

    :param app: The application that the sandbox belongs to.
    :param target: The target that all the sandboxes should run in.
    """

    # The timeout for creating a sandbox, in seconds
    create_timeout = 30

    def __init__(self, app: Application, target: str):
        self.app = app
        self.kres_app = AgentSandboxKresApp(paas_app_id=app.code, tenant_id=app.tenant_id, target=target)

    def provision(self, sandbox_obj: Sandbox) -> "KubernetesPodSandbox":
        """Provision a sandbox by a sandbox record in database.

        :param sandbox_obj: The sandbox object from db.
        :return: The sandbox client.
        """
        env: dict[str, str] = {
            **copy.deepcopy(sandbox_obj.env_vars),
            "TOKEN": sandbox_obj.daemon_token,
            "SERVER_PORT": str(DAEMON_BIND_PORT),
        }

        sandbox = AgentSandbox.create(
            self.kres_app,
            name=sandbox_obj.name,
            sandbox_id=sandbox_obj.uuid.hex,
            workdir=sandbox_obj.workspace,
            snapshot=sandbox_obj.snapshot,
            snapshot_entrypoint=sandbox_obj.snapshot_entrypoint,
            env=env,
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

        # 下发 NodePort 类型的 service, 关联到 sandbox pod, 以暴露 daemon 服务
        sandbox_svc = AgentSandboxService.create(sandbox, sandbox_obj.daemon_port)
        try:
            agent_sandbox_svc_kmodel.create(sandbox_svc)
        except ApiException as exc:
            raise SandboxError("failed to create sandbox service") from KresAgentSandboxError(str(exc), exc)

        return KubernetesPodSandbox(sandbox, sandbox_obj.daemon_endpoint, sandbox_obj.daemon_token)

    def destroy_by_name(self, name: str) -> None:
        """Destroy a sandbox by its name"""
        try:
            agent_sandbox_kmodel.delete_by_name(self.kres_app, name, non_grace_period=True)
            # service name 和 pod name 相同
            agent_sandbox_svc_kmodel.delete_by_name(self.kres_app, name, non_grace_period=True)
        except ApiException as exc:
            raise SandboxError("failed to delete sandbox pod") from KresAgentSandboxError(str(exc), exc)

    def destroy(self, sbx: "KubernetesPodSandbox") -> None:
        self.destroy_by_name(sbx.entity.name)

    def get_from_db_record(self, sandbox_obj: Sandbox) -> "KubernetesPodSandbox":
        """Build a runtime sandbox client from a Sandbox record in database."""
        try:
            entity = AgentSandbox.create(
                self.kres_app,
                name=sandbox_obj.name,
                sandbox_id=sandbox_obj.uuid.hex,
                workdir=sandbox_obj.workspace,
                snapshot=sandbox_obj.snapshot,
                snapshot_entrypoint=sandbox_obj.snapshot_entrypoint,
                env=sandbox_obj.env_vars,
            )
        except ValueError as exc:
            raise SandboxError("invalid sandbox configuration") from exc
        return KubernetesPodSandbox(entity, sandbox_obj.daemon_endpoint, sandbox_obj.daemon_token)

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
    """Sandbox implementation backed by a Kubernetes Pod with daemon service.

    This class uses a daemon HTTP service running inside the Pod for process
    execution and filesystem operations, while still using Kubernetes API for
    Pod lifecycle management (status, logs).

    :param entity: The AgentSandbox entity containing sandbox configuration.
    :param daemon_endpoint: The daemon service endpoint (e.g., "127.0.0.1:8080").
    :param daemon_token: The authentication token for the daemon service.
    """

    def __init__(self, entity: AgentSandbox, daemon_endpoint: str, daemon_token: str):
        self.entity = entity
        self.daemon_endpoint = daemon_endpoint
        self.daemon_token = daemon_token
        self.kres_app = self.entity.app
        self.namespace = self.kres_app.namespace

    def exec(
        self, cmd: list[str] | str, cwd: str | None = None, env_vars: dict | None = None, timeout: int = 60
    ) -> ExecResult:
        """Execute a command inside the sandbox via daemon API.

        :param cmd: The command to execute, can be a string or a list of strings.
        :param cwd: The working directory, defaults to the sandbox's workdir.
        :param env_vars: The environment variables to set, defaults to empty.
        :param timeout: The timeout for the command execution, in seconds.
        """
        cwd = cwd or self.entity.workdir
        env_vars = env_vars or {}

        # Build the command string with environment variables
        cmd_str = self._build_command_string(cmd, env_vars)

        try:
            with self.daemon_client() as client:
                result = client.execute(command=cmd_str, cwd=cwd, timeout=timeout)
                # The daemon API returns combined output, we put it in stdout
                # and leave stderr empty since the daemon doesn't separate them
                return ExecResult(stdout=result.output, stderr="", exit_code=result.exit_code)
        except SandboxDaemonAPIError as exc:
            raise SandboxExecError(f"failed to execute command: {exc}")

    def code_run(self, content: str, language: str = "Python") -> CodeRunResult:
        """Run a piece of code inside the sandbox."""
        if language.lower() != "python":
            raise SandboxError(f"unsupported language: {language}")

        # TODO 通过 base64 等方式, 提升 content 安全性
        result = self.exec(["python", "-c", content], cwd=self.entity.workdir)
        return CodeRunResult(stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code)

    def create_folder(self, path: str, mode: str) -> None:
        """Create a folder inside the sandbox via daemon API.

        :param path: The path of the folder to create.
        :param mode: The permission mode (e.g., "0755").
        """
        try:
            with self.daemon_client() as client:
                client.create_folder(path=path, mode=mode)
        except SandboxDaemonAPIError as exc:
            raise SandboxFileError(f"failed to create folder: {exc}")

    def upload_file(self, file: bytes, remote_path: str, timeout: int = 30 * 60) -> None:
        """Upload a file to the sandbox via daemon API.

        :param file: The file content as bytes.
        :param remote_path: The destination path in the sandbox.
        :param timeout: The timeout for the upload in seconds.
        """
        try:
            with self.daemon_client() as client:
                client.upload_file(file_content=file, dest_path=remote_path, timeout=timeout)
        except SandboxDaemonAPIError as exc:
            raise SandboxFileError(f"failed to upload file: {exc}")

    def delete_file(self, path: str, recursive: bool = False) -> None:
        """Delete a file from the sandbox via daemon API.

        :param path: The path of the file to delete.
        :param recursive: Must be True to delete directories recursively.
        """
        try:
            with self.daemon_client() as client:
                client.delete_file(path=path, recursive=recursive)
        except SandboxDaemonAPIError as exc:
            raise SandboxFileError(f"failed to delete file: {exc}")

    def download_file(self, remote_path: str, timeout: int = 30 * 60) -> bytes:
        """Download a file from the sandbox via daemon API.

        :param remote_path: The path of the file to download.
        :param timeout: The timeout for the download in seconds.
        :returns: The file content as bytes.
        """
        try:
            with self.daemon_client() as client:
                return client.download_file(path=remote_path, timeout=timeout)
        except SandboxDaemonAPIError as exc:
            raise SandboxFileError(f"failed to download file: {exc}")

    def daemon_client(self) -> SandboxDaemonClient:
        """Get the daemon client for this sandbox."""
        # TODO: 将 SandboxDaemonClient 缓存为实例属性（lazy init），或者至少在 KubernetesPodSandbox 级别共享同一个 session?
        return SandboxDaemonClient(self.daemon_endpoint, self.daemon_token)

    def get_status(self) -> str:
        """Get the current status of the sandbox.

        Note: This still uses Kubernetes API as the daemon doesn't provide status info.
        """
        try:
            sandbox = agent_sandbox_kmodel.get(self.kres_app, self.entity.name)
        except AppEntityNotFound as exc:
            raise SandboxError("sandbox not found") from exc
        else:
            return sandbox.status

    def get_logs(self, tail_lines: int | None = None, timestamps: bool = False) -> str:
        """Get the logs of the sandbox.

        Note: This still uses Kubernetes API as the daemon doesn't provide logs.
        """
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

    def _build_command_string(self, cmd: list[str] | str, env_vars: dict) -> str:
        """Build the command string with environment variables.

        :param cmd: The command to execute, can be a string or a list of strings.
        :param env_vars: The environment variables to set.
        :returns: The complete command string.
        """
        cmd_str = cmd if isinstance(cmd, str) else " ".join(shlex.quote(item) for item in cmd)

        if not env_vars:
            return cmd_str

        # Build environment variable exports
        env_exports = " ".join(
            f"{self._validate_env_key(key)}={shlex.quote(str(value))}" for key, value in env_vars.items()
        )
        return f"export {env_exports}; {cmd_str}"

    @staticmethod
    def _validate_env_key(key: object) -> str:
        """Validate that the environment variable key is valid."""

        key_str = str(key)
        if not ENV_KEY_PATTERN.fullmatch(key_str):
            raise SandboxError(f"invalid environment variable key: {key_str!r}")
        return key_str
