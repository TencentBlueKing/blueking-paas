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

from dataclasses import dataclass, field

from attrs import define
from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import DAEMON_BIND_PORT, DAEMON_COMMAND
from paas_wl.bk_app.agent_sandbox.kres_slzs import (
    AgentSandboxDeserializer,
    AgentSandboxSerializer,
    AgentSandboxServiceDeserializer,
    AgentSandboxServiceSerializer,
    ServicePortPair,
)
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.infras.resources.kube_res.base import KresAppEntity, KresAppEntityManager


@define
class AgentSandboxKresApp:
    """The KresApp definition for AgentSandbox.

    - Application not WlApp scoped(no different ns for envs);
    - Always use the default cluster in tenant.

    :param paas_app_id: The PaaS application ID.
    :param tenant_id: The tenant ID where the application is located.
    :param target: The target of the app, this value determines the cluster which the sandboxes
        will run in.
    :param region: The region of the application, optional.
    """

    paas_app_id: str
    tenant_id: str
    target: str
    region: str = settings.DEFAULT_REGION_NAME

    # The namespace where the resources are created
    namespace: str = ""
    # The safe app id for usage in k8s resources' names
    _safe_app_id: str = ""

    def __attrs_post_init__(self):
        self._safe_app_id = self.paas_app_id.replace("_", "0us0")
        self.namespace = f"bk-agent-sbx-{self._safe_app_id}"

    def get_kube_api_client(self) -> EnhancedApiClient:
        """Get the kubernetes API client for current app."""
        if self.target:
            # TODO 考虑在集群信息中增加用途描述, 再校验
            return get_client_by_cluster_name(self.target)

        raise ValueError("missing valid target")


@dataclass
class AgentSandbox(KresAppEntity):
    """Agent sandbox backed by a Pod.

    :param sandbox_id: The unique ID of the sandbox.
    :param workdir: The working directory inside the sandbox.
    :param image: The container image used in the sandbox.
    :param command: The command to run in the sandbox. Always set to /usr/local/bin/daemon.
    :param args: The arguments to pass to the command (/usr/local/bin/daemon).
    :param env: The environment variables set in the sandbox.
    :param status: The current status of the sandbox.
    """

    sandbox_id: str
    workdir: str
    image: str
    env: dict[str, str] = field(default_factory=dict)
    command: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    status: str = "Pending"

    def __post_init__(self):
        # 此处强制覆盖
        self.command = DAEMON_COMMAND

    class Meta:
        kres_class = kres.KPod
        serializer = AgentSandboxSerializer
        deserializer = AgentSandboxDeserializer

    @classmethod
    def create(
        cls,
        app: AgentSandboxKresApp,
        name: str,
        sandbox_id: str,
        workdir: str,
        snapshot: str,
        snapshot_entrypoint: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> "AgentSandbox":
        """Create an AgentSandbox instance.

        :param app: The AgentSandboxKresApp instance.
        :param name: The name of the sandbox.
        :param sandbox_id: The unique ID of the sandbox.
        :param workdir: The working directory inside the sandbox.
        :param snapshot: The snapshot to use for the sandbox.
        :param snapshot_entrypoint: The snapshot_entrypoint to be used as args for the command.
        :param env: The environment variables to set in the sandbox.
        :return: A new AgentSandbox instance.
        """
        return cls(
            app=app,
            name=name,
            sandbox_id=sandbox_id,
            workdir=workdir,
            image=snapshot,
            env=env or {},
            args=snapshot_entrypoint or [],
        )


@dataclass
class AgentSandboxService(KresAppEntity):
    """Agent sandbox service backed by a Kubernetes Service.

    This service exposes the agent sandbox pod to allow external access to the daemon process
    running inside the sandbox.

    :param ports: The list of service port pairs that map service ports to container ports.
    :param sandbox_id: The unique ID of the sandbox that this service is associated with.
    """

    ports: list[ServicePortPair]
    sandbox_id: str

    class Meta:
        kres_class = kres.KService
        serializer = AgentSandboxServiceSerializer
        deserializer = AgentSandboxServiceDeserializer

    @classmethod
    def create(cls, sandbox: AgentSandbox, node_port: int) -> "AgentSandboxService":
        ports = [
            ServicePortPair(name="daemon", port=DAEMON_BIND_PORT, target_port=DAEMON_BIND_PORT, node_port=node_port)
        ]
        return cls(app=sandbox.app, name=sandbox.name, ports=ports, sandbox_id=sandbox.sandbox_id)


agent_sandbox_kmodel: KresAppEntityManager[AgentSandbox, AgentSandboxKresApp] = KresAppEntityManager(AgentSandbox)
agent_sandbox_svc_kmodel: KresAppEntityManager[AgentSandboxService, AgentSandboxKresApp] = KresAppEntityManager(
    AgentSandboxService
)
