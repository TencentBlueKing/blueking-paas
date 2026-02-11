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

from typing import TYPE_CHECKING, Any, Dict, Optional

from attrs import define
from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.agent_sandbox.constants import (
    DEFAULT_IMAGE,
    DEFAULT_RESOURCES,
    DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS,
)
from paas_wl.infras.resources.kube_res.base import KresAppEntityDeserializer, KresAppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp, AgentSandboxService


@define
class ServicePortPair:
    name: str
    port: int
    target_port: int
    node_port: int
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
            "resources": DEFAULT_RESOURCES,
            "env": env,
            "imagePullPolicy": "IfNotPresent",
        }
        if obj.workdir:
            main_container["workingDir"] = obj.workdir

        return {
            "restartPolicy": "Never",
            "terminationGracePeriodSeconds": DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS,
            "containers": [main_container],
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
        sandbox_id = AgentSandboxLabels.parse_sandbox_id(labels)

        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            sandbox_id=sandbox_id,
            workdir=workdir,
            image=getattr(main_container, "image", DEFAULT_IMAGE),
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
                "type": "NodePort",
                "ports": [
                    {
                        "name": port.name,
                        "port": port.port,
                        "targetPort": port.target_port,
                        "protocol": port.protocol,
                        "nodePort": port.node_port,
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
                node_port=getattr(p, "nodePort", 0),
            )
            for p in kube_data.spec.ports
        ]
        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            ports=ports,
            sandbox_id=AgentSandboxLabels.parse_sandbox_id(kube_data.metadata.labels),
        )


class AgentSandboxLabels:
    """Generate and parse labels for an agent sandbox Pod."""

    key_sandbox_id = "bkapp.paas.bk.tencent.com/sandbox-id"

    @classmethod
    def parse_sandbox_id(cls, labels: dict[str, str]) -> str:
        """Parse sandbox id from an agent sandbox Pod.

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
