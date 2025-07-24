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

import datetime
import random
from collections import defaultdict
from typing import Dict, List

from paas_wl.infras.cluster.constants import ClusterComponentName, HelmChartDeployStatus
from paas_wl.infras.cluster.entities import DeployResult, HelmChart, HelmRelease
from paas_wl.infras.cluster.models import Cluster
from paasng.plat_mgt.infras.clusters.values.constructors import get_values_constructor_cls


class StubHelmClient:
    """从集群中获取 Helm Release 信息（仅供单元测试使用）"""

    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name
        self.cluster = Cluster.objects.get(name=cluster_name)

    def list_releases(self, namespace: str | None = None) -> List[HelmRelease]:
        return self._filter_latest_version(self._gen_fake_releases(namespace))

    def get_release(self, name: str, namespace: str | None = None) -> HelmRelease | None:
        for rel in self.list_releases(namespace):
            if rel.name == name:
                return rel

        return None

    @staticmethod
    def _filter_latest_version(releases: List[HelmRelease]) -> List[HelmRelease]:
        """过滤出最新的 Helm Release"""
        release_map: Dict[str, HelmRelease] = {}
        for rel in releases:
            if rel.name not in release_map or rel.version > release_map[rel.name].version:
                release_map[rel.name] = rel

        return list(release_map.values())

    def _gen_fake_releases(self, namespace: str | None = None) -> List[HelmRelease]:
        helm_releases = []
        component_namespace_map: Dict[ClusterComponentName, str] = {}
        component_release_counter: Dict[ClusterComponentName, int] = defaultdict(int)

        for _ in range(50):
            component_name = random.choice(ClusterComponentName.get_values())
            # GPA 不是必须组件，默认不安装
            if component_name == ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER:
                continue

            # 同名组件放在一样的命名空间下
            namespace = (
                namespace or component_namespace_map.get(component_name) or self.cluster.component_preferred_namespace
            )
            component_namespace_map[component_name] = namespace

            # 同名组件的版本号递增
            component_release_counter[component_name] += 1
            version = component_release_counter[component_name]

            helm_releases.append(
                HelmRelease(
                    name=component_name,
                    namespace=namespace,
                    version=version,
                    chart=HelmChart(
                        name=component_name,
                        version=f"{version}.0.0",
                        app_version=f"{version}.0.0",
                        description=component_name,
                    ),
                    deploy_result=DeployResult(
                        status=self._get_fake_status(component_name),
                        description=f"{component_name} installed successfully",
                        created_at=datetime.datetime.now(),
                    ),
                    values=get_values_constructor_cls(component_name)(self.cluster).construct({}),
                    resources=[],
                    secret_name=f"sh.helm.release.v1.{component_name}.v{version}",
                )
            )

        return helm_releases

    def _get_fake_status(self, comp_name: str) -> HelmChartDeployStatus:
        if comp_name == ClusterComponentName.BK_INGRESS_NGINX:
            return HelmChartDeployStatus.DEPLOYED

        if comp_name == ClusterComponentName.BKPAAS_APP_OPERATOR:
            return HelmChartDeployStatus.PENDING_INSTALL

        return HelmChartDeployStatus.FAILED
