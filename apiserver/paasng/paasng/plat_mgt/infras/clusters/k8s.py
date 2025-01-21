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

from typing import Any, Dict, List

from kubernetes.dynamic import ResourceInstance

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KDaemonSet, KDeployment, KStatefulSet
from paasng.plat_mgt.infras.clusters.entities import HelmRelease


class K8SWorkloadStateGetter:
    """
    k8s 工作负载状态获取器

    根据 HelmRelease 中记录的资源信息，获取组件工作负载的状态
    使用场景：集群/平台管理员通过页面可以查看组件部署情况
    （目前支持 Deployment、StatefulSet、DaemonSet 的状态获取）
    """

    def __init__(self, cluster_name: str, release: HelmRelease):
        self.client = get_client_by_cluster_name(cluster_name)
        self.release = release

    def get_states(self) -> List[Dict[str, Any]]:
        if not self.release.resources:
            return []

        return [
            self._get_state(res["kind"], self.release.namespace, res["metadata"]["name"])
            for res in self.release.resources
            if res["kind"] in [KDeployment.kind, KStatefulSet.kind, KDaemonSet.kind]
        ]

    def _get_state(self, kind: str, namespace: str, name: str) -> Dict[str, Any]:
        """获取工作负载资源状态"""
        kres_client, gen_summary_func = {
            KDeployment.kind: (KDeployment, self._gen_deployment_summary),
            KStatefulSet.kind: (KStatefulSet, self._gen_statefulset_summary),
            KDaemonSet.kind: (KDaemonSet, self._gen_daemonset_summary),
        }[kind]

        state = {"name": name, "kind": kind, "summary": "", "conditions": []}

        try:
            res = kres_client(self.client).get(namespace=namespace, name=name)
        except ResourceMissing:
            state["summary"] = "resource missing"
        except Exception:
            state["summary"] = "unknown error"
        else:
            state["summary"] = gen_summary_func(res)
            state["conditions"] = res.status.get("conditions", [])

        return state

    def _gen_deployment_summary(self, res: ResourceInstance) -> str:
        ready = res.status.get("readyReplicas", 0)
        replicas = res.spec.get("replicas", 0)
        updated = res.status.get("updatedReplicas", 0)
        available = res.status.get("availableReplicas", 0)
        return f"Ready: {ready}/{replicas}, Up-to-date: {updated}, Available: {available}"

    def _gen_statefulset_summary(self, res: ResourceInstance) -> str:
        ready = res.status.get("readyReplicas", 0)
        replicas = res.spec.get("replicas", 0)
        updated = res.status.get("updatedReplicas", 0)
        return f"Ready: {ready}/{replicas}, Up-to-date: {updated}"

    def _gen_daemonset_summary(self, res: ResourceInstance) -> str:
        desired = res.status.get("desiredNumberScheduled", 0)
        current = res.status.get("currentNumberScheduled", 0)
        ready = res.status.get("numberReady", 0)
        updated = res.status.get("updatedNumberScheduled", 0)
        available = res.status.get("numberAvailable", 0)
        return f"Desired: {desired}, Current: {current}, Ready: {ready}, Up-to-date: {updated}, Available: {available}"
