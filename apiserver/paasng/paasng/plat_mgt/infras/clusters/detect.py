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
from typing import List

from attr import define

from paas_wl.bk_app.applications.models.config import Config as WlAppConfig
from paas_wl.infras.cluster.models import Cluster, ClusterAllocationPolicy


@define
class AppModuleEnv:
    app_code: str
    module_name: str
    environment: str

    def __hash__(self):
        return hash((self.app_code, self.module_name, self.environment))


@define
class ClusterUsageState:
    """集群被使用的状态"""

    cluster_name: str
    # 可用租户 ID 列表
    available_tenant_ids: List[str]
    # 已绑定分配规则的租户 ID 列表
    allocated_tenant_ids: List[str]
    # 已绑定的应用环境数量
    bind_app_module_envs: List[AppModuleEnv]


class ClusterUsageDetector:
    """集群使用情况"""

    def __init__(self, cluster: Cluster):
        self.cluster = cluster

    def detect(self) -> ClusterUsageState:
        return ClusterUsageState(
            cluster_name=self.cluster.name,
            available_tenant_ids=self.cluster.available_tenant_ids,
            allocated_tenant_ids=self._get_allocated_tenant_ids(),
            bind_app_module_envs=self._get_bind_app_module_envs(),
        )

    def _get_allocated_tenant_ids(self) -> List[str]:
        allocated_tenant_ids = set()

        # 需要针对所有分配策略中的所有规则逐一检查（分配策略数量 <= 租户数量，总体可控）
        for policy in ClusterAllocationPolicy.objects.all():
            for rule in policy.rules:
                if self.cluster.name in rule.clusters:
                    allocated_tenant_ids.add(policy.tenant_id)
                else:
                    for clusters in rule.env_clusters.values():
                        if self.cluster.name in clusters:
                            allocated_tenant_ids.add(policy.tenant_id)

        return list(allocated_tenant_ids)

    def _get_bind_app_module_envs(self) -> List[AppModuleEnv]:
        # 理论上 WlApp & Config 应该是一一对应的，但是由于使用的是 ForeignKey，
        # 可能会出现重复 Config 的情况（脏数据），这里使用 set 来做下去重
        app_module_envs = set()

        for cfg in WlAppConfig.objects.filter(cluster=self.cluster.name):
            app_code = cfg.metadata.get("paas_app_code")
            module_name = cfg.metadata.get("module_name")
            environment = cfg.metadata.get("environment")

            if app_code and module_name and environment:
                app_module_envs.add(AppModuleEnv(app_code=app_code, module_name=module_name, environment=environment))

        return list(app_module_envs)
