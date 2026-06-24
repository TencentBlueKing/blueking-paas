# -*- coding: utf-8 -*-
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

import copy
import logging
import re
import shlex
import uuid
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.agent_sandbox.cluster import get_router_endpoint
from paas_wl.bk_app.agent_sandbox.constants import DAEMON_BIND_PORT
from paas_wl.bk_app.agent_sandbox.exceptions import KresAgentSandboxError
from paas_wl.bk_app.agent_sandbox.image_credential import ensure_image_credential
from paas_wl.bk_app.agent_sandbox.kres_entities import (
    AgentSandbox,
    AgentSandboxKresApp,
    AgentSandboxService,
    VolumeMount,
    agent_sandbox_kmodel,
    agent_sandbox_svc_kmodel,
)
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.constants import (
    DEFAULT_SANDBOX_CPU,
    DEFAULT_SANDBOX_MEMORY,
    SANDBOX_DEFAULT_TTL_SECONDS,
    SandboxStatus,
)
from paasng.platform.agent_sandbox.daemon_client import SandboxDaemonClient
from paasng.platform.agent_sandbox.entities import CodeRunResult, ExecResult
from paasng.platform.agent_sandbox.exceptions import (
    SandboxCreateError,
    SandboxCreateTimeout,
    SandboxDaemonAPIError,
    SandboxError,
    SandboxExecError,
    SandboxFileError,
)
from paasng.platform.agent_sandbox.fs import SandboxFS
from paasng.platform.agent_sandbox.image_validator import check_snapshot_image_exists
from paasng.platform.agent_sandbox.models import Sandbox, SandboxAppSettings, Volume
from paasng.platform.agent_sandbox.process import SandboxProcess
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


ENV_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _build_volume_mounts(application: Application, raw: list[dict] | None) -> list[VolumeMount]:
    """Resolve user-supplied volume_mounts into concrete Pod spec entries.

    Looks up each ``volume_id`` in the database to obtain the CFS subPath.
    Returns an empty list when the feature is disabled or no mounts are requested.

    :param application: The application that owns the Volumes.
    :param raw: The validated list of raw dicts from the request serializer.
        Each item: ``{"volume_id": UUID, "mount_path": str}``.
    """
    if not raw or not settings.AGENT_SANDBOX_VOLUME_ENABLED:
        return []

    volume_ids = [uuid.UUID(str(item["volume_id"])) for item in raw]
    volumes = {
        str(v.uuid): v
        for v in Volume.objects.filter(
            uuid__in=volume_ids,
            application=application,
            deleted_at__isnull=True,
        )
    }

    result: list[VolumeMount] = []
    for item in raw:
        volume = volumes.get(str(item["volume_id"]))
        if volume is None:
            raise error_codes.AGENT_SANDBOX_VOLUME_NOT_FOUND
        result.append(
            VolumeMount(
                volume_id=str(volume.uuid),
                mount_path=item["mount_path"],
                sub_path=volume.storage_path,
                read_only=False,
            )
        )
    return result


def resolve_sandbox_resources(application: Application) -> tuple[Decimal, Decimal]:
    """Resolve the CPU/memory limits for an application's sandboxes.

    Resource limits are not provided by end users. They are decided by an optional
    per-app config maintained by platform operators; apps without a config (or with a
    config that leaves cpu/memory unset) fall back to the platform default for that field.

    :param application: The application that the sandbox belongs to.
    :returns: A ``(cpu, memory)`` tuple, where ``cpu`` is in cores and
        ``memory`` is in GB.
    """
    config = SandboxAppSettings.objects.filter(application=application).first()
    cpu = config.cpu if config and config.cpu is not None else DEFAULT_SANDBOX_CPU
    memory = config.memory if config and config.memory is not None else DEFAULT_SANDBOX_MEMORY
    return cpu, memory


def create_sandbox(
    application: Application,
    creator: str,
    name: str | None = None,
    env_vars: dict | None = None,
    snapshot: str | None = None,
    snapshot_entrypoint: list | None = None,
    workspace: str | None = None,
    ttl_seconds: int = SANDBOX_DEFAULT_TTL_SECONDS,
    volume_mounts: list[dict] | None = None,
) -> Sandbox:
    """Create an agent sandbox record and its corresponding resources.

    :param application: The application that the sandbox belongs to.
    :param creator: The creator of the sandbox.
    :param name: The name of the sandbox, optional.
    :param env_vars: The environment variables dict, optional.
    :param snapshot: The snapshot name, optional.
    :param snapshot_entrypoint: The snapshot entrypoint command list, optional.
    :param workspace: The workspace path, optional.
    :param ttl_seconds: The sandbox ttl in seconds, optional.
    :param volume_mounts: The validated list of shared volume mount requests
        (each item: ``{"volume_id": UUID, "mount_path": str}``). Persisted to
        the Sandbox DB record and resolved into Pod spec mounts during provision.
    """
    # Pre-validate that the snapshot image exists in the registry before creating resources.
    # This avoids a long timeout when the pod tries to pull a non-existent image.
    # Skip validation for the default image — it is platform-maintained and expected to exist.
    snapshot_image = snapshot or settings.AGENT_SANDBOX_DEFAULT_IMAGE
    if snapshot:
        check_snapshot_image_exists(snapshot_image)

    # 资源限制不由用户指定, 而是按 app 级配置回退平台默认值解析
    cpu, memory = resolve_sandbox_resources(application)

    sandbox_obj = Sandbox.objects.new(
        application=application,
        name=name,
        snapshot=snapshot_image,
        snapshot_entrypoint=snapshot_entrypoint,
        env_vars=env_vars,
        creator=creator,
        workspace=workspace,
        ttl_seconds=ttl_seconds,
        volume_mounts=volume_mounts,
        cpu=cpu,
        memory=memory,
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
    # 探测沙箱 daemon 服务就绪的最大超时时间，不宜超过 daemon 实际配置的 PRE_START_TIMEOUT 时间
    create_timeout = 120

    def __init__(self, app: Application, target: str):
        self.app = app
        self.kres_app = AgentSandboxKresApp(paas_app_id=app.code, tenant_id=app.tenant_id, target=target)

    def provision(
        self,
        sandbox_obj: Sandbox,
    ) -> "KubernetesPodSandbox":
        """Provision a sandbox by a sandbox record in database.

        :param sandbox_obj: The sandbox object from db.
        :return: The sandbox client.
        """

        # TODO: 考虑增加一张关联表，记录 volume 被哪些沙箱使用了， 同时用于审计
        volume_mounts = _build_volume_mounts(sandbox_obj.application, sandbox_obj.volume_mounts or None)

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
            volume_mounts=volume_mounts,
            cpu=sandbox_obj.cpu,
            memory=sandbox_obj.memory,
        )
        sandbox_created = False
        try:
            with self.kres_app.get_kube_api_client() as client:
                NamespacesHandler(client).ensure_namespace(self.kres_app.namespace)
                ensure_image_credential(client=client, namespace=self.kres_app.namespace)
            agent_sandbox_kmodel.create(sandbox)
            sandbox_created = True
            self._wait_for_running(sandbox.name)
        except ReadTargetStatusTimeout as exc:
            self._cleanup_sandbox_on_create_error(sandbox.name, sandbox_created)
            raise SandboxCreateTimeout(str(exc)) from exc
        except SandboxCreateError:
            self._cleanup_sandbox_on_create_error(sandbox.name, sandbox_created)
            raise
        except ApiException as exc:
            self._cleanup_sandbox_on_create_error(sandbox.name, sandbox_created)
            raise SandboxError("failed to create sandbox pod") from KresAgentSandboxError(str(exc), exc)

        # 下发 ClusterIP 类型的 service, 关联到 sandbox pod, 由 'Agent Sandbox Router' 进行流量转发
        sandbox_svc = AgentSandboxService.create(sandbox)
        try:
            agent_sandbox_svc_kmodel.create(sandbox_svc)
        except ApiException as exc:
            raise SandboxError("failed to create sandbox service") from KresAgentSandboxError(str(exc), exc)

        router_endpoint = get_router_endpoint(self.kres_app.target)
        return KubernetesPodSandbox(
            entity=sandbox,
            router_endpoint=router_endpoint,
            daemon_token=sandbox_obj.daemon_token,
        )

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

        router_endpoint = get_router_endpoint(self.kres_app.target)
        return KubernetesPodSandbox(
            entity=entity,
            router_endpoint=router_endpoint,
            daemon_token=sandbox_obj.daemon_token,
        )

    def _wait_for_running(self, pod_name: str) -> None:
        with self.kres_app.get_kube_api_client() as client:
            pod_phase = kres.KPod(client).wait_for_status(
                name=pod_name,
                target_statuses={PodPhase.RUNNING.value, PodPhase.FAILED.value},
                namespace=self.kres_app.namespace,
                timeout=self.create_timeout,
            )
            if pod_phase == PodPhase.FAILED.value:
                logs = self._get_pod_logs(client, pod_name)
                raise SandboxCreateError("sandbox pod failed to start", logs=logs)

    def _get_pod_logs(self, client, pod_name: str, tail_lines: int = 500) -> str:
        """Get logs from a pod for failed to start.

        :param client: The Kubernetes API client.
        :param pod_name: The name of the pod.
        :returns: The logs content.
        """
        try:
            resp = kres.KPod(client).get_log(
                name=pod_name,
                namespace=self.kres_app.namespace,
                tail_lines=tail_lines,
            )
            return resp.data.decode("utf-8", errors="replace")
        except ApiException:
            logger.exception("failed to get logs from failed pod %s", pod_name)
            return ""

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

    When requesting a pod, the request is first routed to the Agent Sandbox Router
    on the sandbox cluster, which then forwards it to the appropriate sandbox daemon.

    :param entity: The AgentSandbox entity containing sandbox configuration.
    :param router_endpoint: The sandbox router endpoint (e.g., "agent-sandbox-router.example.com").
    :param daemon_token: The authentication token for the daemon service.
    """

    def __init__(self, entity: AgentSandbox, router_endpoint: str, daemon_token: str):
        self.entity = entity
        self.router_endpoint = router_endpoint
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
        return SandboxDaemonClient(
            router_endpoint=self.router_endpoint,
            token=self.daemon_token,
            sandbox_name=self.entity.name,
            sandbox_namespace=self.namespace,
            sandbox_daemon_port=DAEMON_BIND_PORT,
            router_auth_token=settings.AGENT_SANDBOX_ROUTER_AUTH_TOKEN,
        )

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
