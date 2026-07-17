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

from typing import TYPE_CHECKING, Any, Dict, Optional

from attrs import define
from django.conf import settings
from kubernetes.dynamic import ResourceInstance
from kubernetes.utils.quantity import parse_quantity

from paas_wl.bk_app.agent_sandbox.constants import (
    DAEMON_BIND_PORT,
    DEFAULT_RESOURCES,
    DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS,
    SHARED_VOLUME_NAME_IN_POD,
)
from paas_wl.bk_app.agent_sandbox.image_credential import IMAGE_CREDENTIAL_NAME
from paas_wl.infras.resources.kube_res.base import KresAppEntityDeserializer, KresAppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp, AgentSandboxService


@define
class ServicePortPair:
    name: str
    port: int
    target_port: int
    protocol: str = "TCP"


class AgentSandboxSerializer(KresAppEntitySerializer["AgentSandbox"]):
    """The serializer for AgentSandbox entity."""

    def serialize(self, obj: "AgentSandbox", original_obj: Optional[ResourceInstance] = None, **kwargs):
        return {
            "apiVersion": self.get_apiversion(),
            "kind": "Pod",
            "metadata": {
                "name": obj.name,
                "labels": AgentSandboxLabels.generate(obj.sandbox_id),
            },
            "spec": self._construct_pod_spec(obj),
        }

    @staticmethod
    def _construct_pod_spec(obj: "AgentSandbox") -> Dict:
        env = [{"name": key, "value": value} for key, value in obj.env.items()]

        main_container = {
            "name": "main",
            "image": obj.image,
            "command": obj.command,
            "args": obj.args,
            "resources": _build_resources(obj.cpu, obj.memory),
            "env": env,
            "imagePullPolicy": "IfNotPresent",
            # startupProbe: 每 1s 探测一次，最多容忍 300 次失败（即等待 ~300s），覆盖沙箱中 pre_start.sh 最长耗时 (沙箱 daemon 服务默认设置 PRE_START_TIMEOUT=300s)
            # NOTE: 沙箱中可能配置了 pre_start.sh，此时 daemon 服务需要等待 pre_start.sh 执行完成后才会就绪
            "startupProbe": {
                "tcpSocket": {
                    "port": DAEMON_BIND_PORT,
                },
                "periodSeconds": 1,
                "failureThreshold": 300,
            },
            # readinessProbe: startup 成功后接管，每 2s 探测一次，连续 2 次失败（~20s）标记为 Not Ready
            "readinessProbe": {
                "tcpSocket": {
                    "port": DAEMON_BIND_PORT,
                },
                "initialDelaySeconds": 0,
                "periodSeconds": 2,
                "failureThreshold": 2,
            },
        }
        if obj.workdir:
            main_container["workingDir"] = obj.workdir

        # 共享挂载：1 个 CSI inline volume + N 个 volumeMounts（通过 subPath 区分）
        volumes: list[dict] = []
        if obj.volume_mounts:
            volumes.append(
                {
                    "name": SHARED_VOLUME_NAME_IN_POD,
                    "csi": _build_csi_volume_source(),
                }
            )
            main_container["volumeMounts"] = [
                {
                    "name": SHARED_VOLUME_NAME_IN_POD,
                    "mountPath": vm.mount_path,
                    "subPath": vm.sub_path,
                    "readOnly": vm.read_only,
                }
                for vm in obj.volume_mounts
            ]

        pod_spec: Dict[str, Any] = {
            "restartPolicy": "Never",
            "terminationGracePeriodSeconds": DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS,
            "imagePullSecrets": [{"name": IMAGE_CREDENTIAL_NAME}],
            "containers": [main_container],
        }
        if volumes:
            pod_spec["volumes"] = volumes
        return pod_spec


def _build_resources(cpu: float, memory: float) -> Dict[str, Dict[str, str]]:
    """Build the container ``resources`` block for a sandbox Pod.

    The ``limits`` are derived from the per-sandbox cpu/memory values (resolved from the
    app-level config or the platform default), while ``requests`` keep the platform
    default values. ``limits`` are guaranteed to be no less than ``requests``.

    :param cpu: The CPU limit in cores (e.g. 2 means 2000m).
    :param memory: The memory limit in GB (e.g. 1 means 1024Mi).
    :returns: A dict with ``limits`` and ``requests`` sub-blocks.
    """
    requests = DEFAULT_RESOURCES["requests"]

    cpu_milli = max(int(round(cpu * 1000)), int(parse_quantity(requests["cpu"]) * 1000))
    memory_mi = max(int(round(memory * 1024)), int(parse_quantity(requests["memory"]) / (1024 * 1024)))

    return {
        "limits": {"cpu": f"{cpu_milli}m", "memory": f"{memory_mi}Mi"},
        "requests": dict(requests),
    }


def _build_csi_volume_source() -> Dict[str, Any]:
    """Build the ``csi`` source block for the shared inline volume.

    The driver and volumeAttributes are fully driven by settings so that any
    RWX-capable CSI driver (Tencent Cloud CFS, NFS, CephFS, ...) can be used
    without code changes: ``AGENT_SANDBOX_VOLUME_CSI_ATTRIBUTES`` is passed
    through as-is, and its keys are defined by the target CSI driver.
    """
    return {
        "driver": settings.AGENT_SANDBOX_VOLUME_CSI_DRIVER,
        "volumeAttributes": dict(settings.AGENT_SANDBOX_VOLUME_CSI_ATTRIBUTES),
    }


class AgentSandboxDeserializer(KresAppEntityDeserializer["AgentSandbox", "AgentSandboxKresApp"]):
    """The deserializer for AgentSandbox entity."""

    def deserialize(self, app: "AgentSandboxKresApp", kube_data: ResourceInstance) -> "AgentSandbox":
        main_container = kube_data.spec.containers[0]
        workdir = getattr(main_container, "workingDir", "")
        # Parse and get env as dict
        env = {
            str(item.name): str(getattr(item, "value", ""))
            for item in (getattr(main_container, "env", None) or [])
            if getattr(item, "name", None)
        }
        labels = kube_data.metadata.labels or {}
        sandbox_id = AgentSandboxLabels.parse(labels)

        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            sandbox_id=sandbox_id,
            workdir=workdir,
            image=getattr(main_container, "image", settings.AGENT_SANDBOX_DEFAULT_IMAGE),
            env=env,
            args=getattr(main_container, "args", []),
            status=self._get_status(kube_data),
        )

    @staticmethod
    def _get_status(pod: ResourceInstance) -> str:
        if not getattr(pod, "status", None):
            return "Pending"

        phase = getattr(pod.status, "phase", None)
        if not phase:
            return "Pending"
        return phase


class AgentSandboxServiceSerializer(KresAppEntitySerializer["AgentSandboxService"]):
    def serialize(self, obj: "AgentSandboxService", original_obj: Optional[ResourceInstance] = None, **kwargs):
        labels = AgentSandboxLabels.generate(obj.sandbox_id)
        body: Dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": obj.name,
                "labels": labels,
            },
            "spec": {
                "type": "ClusterIP",
                "ports": [
                    {
                        "name": port.name,
                        "port": port.port,
                        "targetPort": port.target_port,
                        "protocol": port.protocol,
                    }
                    for port in obj.ports
                ],
                "selector": labels,
            },
        }

        if original_obj:
            body["metadata"]["resourceVersion"] = original_obj.metadata.resourceVersion

        return body


class AgentSandboxServiceDeserializer(KresAppEntityDeserializer["AgentSandboxService", "AgentSandboxKresApp"]):
    def deserialize(self, app: "AgentSandboxKresApp", kube_data: ResourceInstance) -> "AgentSandboxService":
        ports = [
            ServicePortPair(
                name=p.name,
                port=p.port,
                target_port=p.targetPort,
            )
            for p in kube_data.spec.ports
        ]
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            ports=ports,
            sandbox_id=AgentSandboxLabels.parse(kube_data.metadata.labels),
        )


class AgentSandboxLabels:
    """Generate and parse labels for an agent sandbox Pod."""

    key_sandbox_id = "bkapp.paas.bk.tencent.com/sandbox-id"

    @classmethod
    def parse(cls, labels: dict[str, str]) -> str:
        """Parse labels from an agent sandbox Pod.

        :return: sandbox_id
        """
        sandbox_id = labels.get(cls.key_sandbox_id, "")
        return sandbox_id

    @classmethod
    def generate(cls, sandbox_id: str) -> dict[str, str]:
        """Generate labels for an agent sandbox Pod."""
        return {
            "app.kubernetes.io/managed-by": "bkpaas-agent-sandbox",
            cls.key_sandbox_id: sandbox_id,
        }
