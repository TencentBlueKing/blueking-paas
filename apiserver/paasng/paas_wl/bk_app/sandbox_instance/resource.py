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

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.sandbox_instance.constants import (
    RESTARTED_AT_ANNOTATION,
    SANDBOX_INSTANCE_API_VERSION,
    DesiredState,
)
from paas_wl.bk_app.sandbox_instance.crd import SandboxInstance
from paas_wl.bk_app.sandbox_instance.entities import SandboxInstanceSpec
from paas_wl.bk_app.sandbox_instance.exceptions import (
    SandboxInstanceDeployError,
    SandboxInstanceNotFound,
)
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing

logger = logging.getLogger(__name__)


class SandboxInstanceManager:
    """管理 SandboxInstance CR 的下发、查询、状态控制与删除。

    该管理器只复用底层通用的 CR 下发能力(``SandboxInstance(BaseKresource)``),
    与 BkApp 的 AppModelResource / deploy() / WaitAppModelReady 完全解耦。

    :param cluster_name: 目标集群名。CR 下发到该集群, 由集群侧 sandbox-controller 协调。
    """

    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name

    def deploy(self, spec: SandboxInstanceSpec) -> Dict[str, Any]:
        """下发(创建或更新) SandboxInstance CR。

        仅下发 CR 后立即返回, 就绪状态由异步 poller(WaitSandboxInstanceReady)判定。

        :param spec: 沙箱实例业务参数, 用于拼装 CR manifest。
        :returns: 下发后的 CR dict。
        :raises SandboxInstanceDeployError: 下发失败。
        """
        manifest = spec.build_manifest()
        with get_client_by_cluster_name(self.cluster_name) as client:
            try:
                obj, _ = SandboxInstance(client, api_version=SANDBOX_INSTANCE_API_VERSION).create_or_update(
                    spec.name,
                    namespace=spec.namespace,
                    body=manifest,
                    update_method="replace",
                    auto_add_version=True,
                )
            except ApiException as e:
                logger.exception("failed to deploy SandboxInstance %s/%s", spec.namespace, spec.name)
                raise SandboxInstanceDeployError(str(e)) from e

        return obj.to_dict()

    def get(self, namespace: str, name: str) -> Dict[str, Any]:
        """查询 SandboxInstance CR。

        :raises SandboxInstanceNotFound: CR 不存在。
        """
        with get_client_by_cluster_name(self.cluster_name) as client:
            try:
                obj = SandboxInstance(client, api_version=SANDBOX_INSTANCE_API_VERSION).get(
                    name, namespace=namespace
                )
            except ResourceMissing as e:
                raise SandboxInstanceNotFound(f"{namespace}/{name}") from e
        return obj.to_dict()

    def set_desired_state(self, namespace: str, name: str, desired_state: DesiredState) -> Dict[str, Any]:
        """通过 patch spec.desiredState 停止 / 启动沙箱。

        - Stopped: operator 删除 Pod 但保留 CR 与持久盘(PVC)。
        - Running: operator 复用原持久盘重新创建 Pod。
        """
        patch_body = {"spec": {"desiredState": desired_state.value}}
        return self._patch(namespace, name, patch_body)

    def restart(self, namespace: str, name: str) -> Dict[str, Any]:
        """通过 restartedAt 注解触发一次重调度重启(删 Pod 重建, 复用持久盘)。"""
        restarted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        patch_body = {"metadata": {"annotations": {RESTARTED_AT_ANNOTATION: restarted_at}}}
        return self._patch(namespace, name, patch_body)

    def delete(self, namespace: str, name: str) -> None:
        """删除 SandboxInstance CR。

        依赖对象的回收由 CR 的 spec.retention 控制(缺省 pod=Delete, pvc=Retain)。
        """
        with get_client_by_cluster_name(self.cluster_name) as client:
            try:
                SandboxInstance(client, api_version=SANDBOX_INSTANCE_API_VERSION).delete(name, namespace=namespace)
            except ResourceMissing:
                # 幂等删除: CR 已不存在视为成功
                return
            except ApiException as e:
                logger.exception("failed to delete SandboxInstance %s/%s", namespace, name)
                raise SandboxInstanceDeployError(str(e)) from e

    def _patch(self, namespace: str, name: str, patch_body: Dict[str, Any]) -> Dict[str, Any]:
        with get_client_by_cluster_name(self.cluster_name) as client:
            try:
                obj = SandboxInstance(client, api_version=SANDBOX_INSTANCE_API_VERSION).patch(
                    name, body=patch_body, namespace=namespace
                )
            except ResourceMissing as e:
                raise SandboxInstanceNotFound(f"{namespace}/{name}") from e
            except ApiException as e:
                logger.exception("failed to patch SandboxInstance %s/%s", namespace, name)
                raise SandboxInstanceDeployError(str(e)) from e
        return obj.to_dict()
