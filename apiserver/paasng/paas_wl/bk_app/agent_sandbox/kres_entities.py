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

from dataclasses import dataclass

from attrs import define
from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import DEFAULT_IMAGE
from paas_wl.bk_app.agent_sandbox.kres_slzs import AgentSandboxDeserializer, AgentSandboxSerializer
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
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
    :param region: The region of the application, optional.
    """

    paas_app_id: str
    tenant_id: str
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
        cluster = ClusterAllocator(
            AllocationContext(
                tenant_id=self.tenant_id,
                region=self.region,
                # By default, use the "prod" environment cluster
                environment="prod",
            )
        ).get_default()
        return get_client_by_cluster_name(cluster.name)


@dataclass
class AgentSandbox(KresAppEntity):
    """Agent sandbox backed by a Pod.

    **Only for experimental use.**

    :param sandbox_id: The unique ID of the sandbox.
    :param workdir: The working directory inside the sandbox.
    :param image: The container image used in the sandbox.
    :param status: The current status of the sandbox.
    """

    sandbox_id: str
    workdir: str
    image: str = DEFAULT_IMAGE
    status: str = "Pending"

    class Meta:
        kres_class = kres.KPod
        serializer = AgentSandboxSerializer
        deserializer = AgentSandboxDeserializer

    @classmethod
    def create(
        cls,
        app: AgentSandboxKresApp,
        sandbox_id: str,
        workdir: str,
        image: str,
    ) -> "AgentSandbox":
        """Create an AgentSandbox instance."""
        name = f"sbx-{app._safe_app_id}-{sandbox_id[:8]}"
        return cls(
            app=app,
            name=name,
            sandbox_id=sandbox_id,
            workdir=workdir,
            image=image,
        )


agent_sandbox_kmodel: KresAppEntityManager[AgentSandbox, AgentSandboxKresApp] = KresAppEntityManager(AgentSandbox)
