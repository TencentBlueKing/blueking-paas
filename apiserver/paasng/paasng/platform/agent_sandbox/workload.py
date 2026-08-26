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

"""Workload adapters for agent sandbox K8s resources.

``AgentSandboxPod`` and ``AgentSandboxInstance`` share fields, but create / wait / status /
delete / log routing differ. Keep those differences here so ``AgentSandboxResManager`` stays
workload-type-agnostic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Any, ClassVar

from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.agent_sandbox.constants import SandboxInstancePhase
from paas_wl.bk_app.agent_sandbox.kres_entities import (
    AgentSandboxInstance,
    AgentSandboxKresApp,
    AgentSandboxPod,
    AgentSandboxWorkload,
    VolumeMount,
    agent_sandbox_instance_kmodel,
    agent_sandbox_pod_kmodel,
)
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.constants import SandboxStatus, SandboxWorkloadType
from paasng.platform.agent_sandbox.exceptions import SandboxCreateError, SandboxError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SandboxWorkloadSpec:
    """The workload-kind-agnostic inputs needed to render a sandbox workload.

    Field names mirror ``AgentSandboxWorkload.create`` so handlers can forward them as-is.

    :param name: The name of the sandbox resource.
    :param sandbox_id: The unique ID of the sandbox.
    :param workdir: The working directory inside the sandbox.
    :param snapshot: The container image used in the sandbox.
    :param snapshot_entrypoint: The command args passed to the sandbox daemon.
    :param env: The environment variables to set in the sandbox.
    :param volume_mounts: The resolved shared volume mounts to attach.
    :param cpu: The CPU limit in cores. Falls back to the entity default when unset.
    :param memory: The memory limit in GB. Falls back to the entity default when unset.
    """

    name: str
    sandbox_id: str
    workdir: str
    snapshot: str
    snapshot_entrypoint: list[str] | None = None
    env: dict[str, str] | None = None
    volume_mounts: list[VolumeMount] | None = None
    cpu: float | None = None
    memory: float | None = None


def get_pod_logs(client, namespace: str, pod_name: str, tail_lines: int = 500) -> str:
    """Read the last log lines of a Pod. Empty string if the API call fails."""
    try:
        resp = kres.KPod(client).get_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
        )
        return resp.data.decode("utf-8", errors="replace")
    except ApiException:
        logger.exception("failed to get logs from failed pod %s", pod_name)
        return ""


class SandboxWorkloadHandler(ABC):
    """Operations on one kind of agent sandbox workload, bound to a single ``AgentSandboxKresApp``.

    Subclasses declare the K8s entity type and its teardown semantics, then implement the
    parts that cannot be shared: readiness, status vocabulary and Pod name resolution.

    :param kres_app: The KresApp whose cluster and namespace the workload lives in.
    """

    entity_cls: ClassVar[type[AgentSandboxWorkload]]
    # Distinct generic KresAppEntityManager instantiations, so this cannot be typed more
    # precisely here; only get / create / delete_by_name are used.
    kmodel: ClassVar[Any]
    # Whether deletion should force ``gracePeriodSeconds=0``.
    delete_non_grace_period: ClassVar[bool]

    def __init__(self, kres_app: AgentSandboxKresApp):
        self.kres_app = kres_app

    @property
    def workload_type(self) -> str:
        """The platform ``SandboxWorkloadType`` value this handler serves."""
        return self.entity_cls.workload_type_key

    def build_entity(self, spec: SandboxWorkloadSpec) -> AgentSandboxWorkload:
        """Build an in-memory workload entity (does not apply it to the cluster)."""
        # Shallow copy on purpose: dataclasses.asdict would recurse into the VolumeMount
        # entries and turn them into plain dicts, which the spec builders cannot consume.
        kwargs = {f.name: getattr(spec, f.name) for f in fields(spec)}
        return self.entity_cls.create(self.kres_app, **kwargs)

    def create(self, spec: SandboxWorkloadSpec) -> AgentSandboxWorkload:
        """Build the entity and persist it to the cluster."""
        entity = self.build_entity(spec)
        self.kmodel.create(entity)
        return entity

    def get_status(self, name: str) -> str:
        """Read the workload's current phase as a platform ``SandboxStatus`` value.

        Normalizing here keeps the raw Pod / SandboxInstance phases (which do not share a
        vocabulary) from leaking to callers.
        """
        workload: AgentSandboxWorkload = self.kmodel.get(self.kres_app, name)
        return self.map_status(workload.status)

    def delete(self, name: str) -> None:
        """Delete the workload using the teardown semantics of its kind."""
        self.kmodel.delete_by_name(self.kres_app, name, non_grace_period=self.delete_non_grace_period)

    @abstractmethod
    def wait_until_ready(self, name: str, timeout: float) -> None:
        """Block until the workload is Running, or raise SandboxCreateError on Failed."""

    @abstractmethod
    def map_status(self, phase: str) -> str:
        """Map the workload's raw ``status.phase`` to a platform ``SandboxStatus`` value."""

    @abstractmethod
    def resolve_pod_name(self, client, name: str) -> str:
        """Return the Pod name used to fetch container logs.

        Must be called inside a Kubernetes client context opened by the caller, so that
        resolving the name and reading the logs share one connection.
        """


class PodWorkloadHandler(SandboxWorkloadHandler):
    """Native Kubernetes Pod workload."""

    entity_cls = AgentSandboxPod
    kmodel = agent_sandbox_pod_kmodel
    # Pod teardown is driven by kubelet, so a zero grace period takes effect right away and
    # matches the short DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS the sandbox Pod spec sets.
    delete_non_grace_period = True

    def wait_until_ready(self, name: str, timeout: float) -> None:
        with self.kres_app.get_kube_api_client() as client:
            pod_phase = kres.KPod(client).wait_for_status(
                name=name,
                target_statuses={PodPhase.RUNNING.value, PodPhase.FAILED.value},
                namespace=self.kres_app.namespace,
                timeout=timeout,
            )
            if pod_phase == PodPhase.FAILED.value:
                logs = get_pod_logs(client, self.kres_app.namespace, name)
                raise SandboxCreateError("sandbox pod failed to start", logs=logs)

    def map_status(self, phase: str) -> str:
        """Map Pod ``status.phase``. The sandbox Pod uses ``restartPolicy: Never``, so a
        Succeeded Pod means the daemon exited and the sandbox can no longer serve requests.
        """
        match phase:
            case PodPhase.RUNNING.value:
                return SandboxStatus.RUNNING.value
            case PodPhase.FAILED.value:
                return SandboxStatus.ERR_CREATING.value
            case PodPhase.SUCCEEDED.value:
                return SandboxStatus.STOPPED.value
            case _:
                return SandboxStatus.PENDING.value

    def resolve_pod_name(self, client, name: str) -> str:
        return name


class SandboxInstanceWorkloadHandler(SandboxWorkloadHandler):
    """SandboxInstance CR (cube MicroVM) workload."""

    entity_cls = AgentSandboxInstance
    kmodel = agent_sandbox_instance_kmodel
    # The MicroVM is torn down by sandbox-controller through its finalizer, which needs the
    # default grace period to run; forcing zero only skews the CR's own deletion semantics.
    delete_non_grace_period = False

    def wait_until_ready(self, name: str, timeout: float) -> None:
        with self.kres_app.get_kube_api_client() as client:
            phase = kres.KSandboxInstance(client).wait_for_status(
                name=name,
                target_statuses={SandboxInstancePhase.RUNNING.value, SandboxInstancePhase.FAILED.value},
                namespace=self.kres_app.namespace,
                timeout=timeout,
            )
            if phase == SandboxInstancePhase.FAILED.value:
                logs = self._failure_diagnostics(client, name)
                raise SandboxCreateError("sandbox instance failed to start", logs=logs)

    def map_status(self, phase: str) -> str:
        """Map SandboxInstance CR ``status.phase``; the extra ``Creating`` phase folds into PENDING."""
        match phase:
            case SandboxInstancePhase.RUNNING.value:
                return SandboxStatus.RUNNING.value
            case SandboxInstancePhase.FAILED.value:
                return SandboxStatus.ERR_CREATING.value
            case _:
                return SandboxStatus.PENDING.value

    def resolve_pod_name(self, client, name: str) -> str:
        """SandboxInstance must expose ``status.podName``; do not fall back to label selection."""
        try:
            instance = kres.KSandboxInstance(client).get(name, namespace=self.kres_app.namespace)
        except (ResourceMissing, ApiException) as exc:
            raise SandboxError("sandbox pod not found") from exc

        pod_name = getattr(getattr(instance, "status", None), "podName", None) or ""
        if not pod_name:
            raise SandboxError("sandbox pod not found")
        return pod_name

    def _failure_diagnostics(self, client, name: str) -> str:
        """Collect failure diagnostics for a Failed SandboxInstance.

        Expose ``status.message`` from sandbox-controller; when ``status.podName`` is set,
        also append the last lines of the rendered cube Pod. Internal identifiers such as
        pod/node names are not returned to callers.
        """
        namespace = self.kres_app.namespace
        parts: list[str] = []
        pod_name = ""
        try:
            instance = kres.KSandboxInstance(client).get(name, namespace=namespace)
            status = getattr(instance, "status", None)
            if status:
                message = getattr(status, "message", None) or ""
                pod_name = getattr(status, "podName", None) or ""
                if message:
                    parts.append(message)
        except Exception:
            logger.exception("failed to get SandboxInstance %s status for diagnostics", name)

        if pod_name and (pod_logs := get_pod_logs(client, namespace, pod_name)):
            parts.append(pod_logs)
        return "\n".join(parts)


_HANDLER_CLASSES: dict[str, type[SandboxWorkloadHandler]] = {
    SandboxWorkloadType.DEFAULT.value: PodWorkloadHandler,
    SandboxWorkloadType.SANDBOX_INSTANCE.value: SandboxInstanceWorkloadHandler,
}


def get_workload_handler(kres_app: AgentSandboxKresApp, workload_type: str) -> SandboxWorkloadHandler:
    """Build the handler serving ``workload_type`` in ``kres_app``.

    Never fall back to a default handler: routing an unregistered type to the Pod handler
    would silently read and delete the wrong kind of resource, leaking the real workload.
    """
    try:
        handler_cls = _HANDLER_CLASSES[workload_type]
    except KeyError:
        raise SandboxError(f"unsupported sandbox workload type: {workload_type!r}")
    return handler_cls(kres_app)
