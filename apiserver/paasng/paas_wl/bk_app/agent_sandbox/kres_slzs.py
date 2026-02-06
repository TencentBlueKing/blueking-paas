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

from typing import TYPE_CHECKING, Dict, Optional

from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.agent_sandbox.constants import (
    DEFAULT_COMMAND,
    DEFAULT_IMAGE,
    DEFAULT_RESOURCES,
    DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS,
    DEFAULT_WORKDIR,
)
from paas_wl.infras.resources.kube_res.base import KresAppEntityDeserializer, KresAppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp


class AgentSandboxSerializer(KresAppEntitySerializer["AgentSandbox"]):
    """The serializer for AgentSandbox entity."""

    def serialize(self, obj: "AgentSandbox", original_obj: Optional[ResourceInstance] = None, **kwargs):
        return {
            "apiVersion": self.get_apiversion(),
            "kind": "Pod",
            "metadata": {
                "name": obj.name,
                "labels": AgentSandboxLabels.generate(obj.app._safe_app_id, obj.sandbox_id),
            },
            "spec": self._construct_pod_spec(obj),
        }

    def _construct_pod_spec(self, obj: "AgentSandbox") -> Dict:
        workdir = obj.workdir or DEFAULT_WORKDIR
        vol_name = "workspace"
        return {
            "restartPolicy": "Never",
            "terminationGracePeriodSeconds": DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS,
            "containers": [
                {
                    "name": "main",
                    "image": obj.image,
                    "command": DEFAULT_COMMAND,
                    "workingDir": workdir,
                    "resources": DEFAULT_RESOURCES,
                    "volumeMounts": [{"name": vol_name, "mountPath": workdir}],
                }
            ],
            "volumes": [{"name": vol_name, "emptyDir": {}}],
        }


class AgentSandboxDeserializer(KresAppEntityDeserializer["AgentSandbox", "AgentSandboxKresApp"]):
    """The deserializer for AgentSandbox entity."""

    def deserialize(self, app: "AgentSandboxKresApp", kube_data: ResourceInstance) -> "AgentSandbox":
        main_container = kube_data.spec.containers[0]
        workdir = getattr(main_container, "workingDir", DEFAULT_WORKDIR)
        labels = kube_data.metadata.labels or {}
        _, sandbox_id = AgentSandboxLabels.parse(labels)

        return self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            sandbox_id=sandbox_id,
            workdir=workdir,
            image=getattr(main_container, "image", DEFAULT_IMAGE),
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


class AgentSandboxLabels:
    """Generate and parse labels for an agent sandbox Pod."""

    key_app_id = "bkapp.paas.bk.tencent.com/code"
    key_sandbox_id = "bkapp.paas.bk.tencent.com/sandbox-id"

    @classmethod
    def parse(cls, labels: dict[str, str]) -> tuple[str, str]:
        """Parse labels from an agent sandbox Pod.

        :return: (paas_app_id, sandbox_id)
        """
        paas_app_id = labels.get(cls.key_app_id, "")
        sandbox_id = labels.get(cls.key_sandbox_id, "")
        return paas_app_id, sandbox_id

    @classmethod
    def generate(cls, paas_app_id: str, sandbox_id: str) -> dict[str, str]:
        """Generate labels for an agent sandbox Pod."""
        return {
            "app.kubernetes.io/managed-by": "bkpaas-agent-sandbox",
            cls.key_app_id: paas_app_id,
            cls.key_sandbox_id: sandbox_id,
        }
