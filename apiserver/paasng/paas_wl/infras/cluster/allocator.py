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

from functools import partialmethod
from typing import List

from django.db.models import Case, QuerySet, When

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyType
from paas_wl.infras.cluster.entities import AllocationContext, AllocationPolicy
from paas_wl.infras.cluster.models import Cluster, ClusterAllocationPolicy


class ClusterAllocator:
    """集群分配"""

    def __init__(self, ctx: AllocationContext):
        self.ctx = ctx

    def list(self) -> QuerySet[Cluster]:
        """获取所有可用的集群"""
        return self._list()

    def get(self, cluster_name: str | None) -> Cluster:
        """根据名称获取集群，若不指定，则返回默认集群

        注意：如果只需获取默认集群，请使用 get_default 方法
        """
        clusters = self._list()
        if cluster_name:
            clusters = clusters.filter(name=cluster_name)

        if c := clusters.first():
            return c

        raise ValueError(f"cluster allocator with ctx {self.ctx} and name {cluster_name} got no cluster")

    def check_available(self, cluster_name: str) -> bool:
        """检查指定集群是否可用"""
        return self._list().filter(name=cluster_name).exists()

    # 快捷方法 -> 根据指定的参数，获取默认集群
    get_default = partialmethod(get, cluster_name=None)

    def _list(self) -> QuerySet[Cluster]:
        """获取集群列表"""
        if policy := ClusterAllocationPolicy.objects.filter(tenant_id=self.ctx.tenant_id).first():
            return self._policy_base_list(policy)

        # 未配置策略，返回空集合
        return Cluster.objects.none()

    def _policy_base_list(self, policy: ClusterAllocationPolicy) -> QuerySet[Cluster]:
        """根据策略获取集群列表"""
        cluster_names: List[str] | None = None

        if policy.type == ClusterAllocationPolicyType.UNIFORM and policy.allocation_policy:
            # 统一分配
            cluster_names = self._get_cluster_names_from_policy(policy.allocation_policy)
        elif policy.type == ClusterAllocationPolicyType.RULE_BASED:
            # 按规则分配
            for p in policy.allocation_precedence_policies:
                if p.match(self.ctx):
                    cluster_names = self._get_cluster_names_from_policy(p.policy)
                    break
        else:
            raise ValueError(f"unknown cluster allocation policy type: {policy.type}")

        if not cluster_names:
            raise ValueError(f"no cluster found for policy: {policy}")

        # 由于分配策略认定 cluster_names 中的第一个是默认集群，因此需要特殊排序
        # ref: https://rednafi.com/python/sort_by_a_custom_sequence_in_django/
        order = Case(*(When(name=name, then=pos) for pos, name in enumerate(cluster_names)))
        # 查询并按自定义规则排序
        return Cluster.objects.filter(name__in=cluster_names).order_by(order)

    def _get_cluster_names_from_policy(self, policy: AllocationPolicy) -> List[str] | None:
        """根据策略获取集群名称列表"""
        if policy.env_specific:
            if not policy.env_clusters:
                raise ValueError("env_clusters is required for env_specific policy")

            return policy.env_clusters.get(self.ctx.environment)

        return policy.clusters
