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

from functools import partial
from typing import TYPE_CHECKING, Dict, List, Optional

from django.db.models import QuerySet

from paas_wl.infras.cluster.constants import (
    ClusterAllocationPolicyCondType,
    ClusterAllocationPolicyType,
    ClusterFeatureFlag,
)
from paas_wl.infras.cluster.entities import AllocationContext, AllocationPolicy, AllocationPrecedencePolicy
from paas_wl.infras.cluster.models import Cluster, ClusterAllocationPolicy
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application


def get_exposed_url_type(application: "Application", cluster_name: str | None = None) -> ExposedURLType:
    """Get the exposed url type.

    :param region: The region. If given, use the region's default cluster.
    :param cluster_name: The name of cluster. If given, other arguments are ignored.
    """
    if cluster_name:
        cluster = Cluster.objects.get(name=cluster_name)
    else:
        ctx = AllocationContext(
            tenant_id=application.tenant_id,
            region=application.region,
            environment=AppEnvironment.PRODUCTION,
        )
        cluster = ClusterAllocator(ctx).get_default()

    return ExposedURLType(cluster.exposed_url_type)


class EnvClusterService:
    """EnvClusterService provide interface for managing the cluster info of given env"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    def get_cluster(self) -> Cluster:
        """get the cluster bound to the env, if no specific cluster is bound, return default cluster"""
        return Cluster.objects.get(name=self.get_cluster_name())

    def get_cluster_name(self) -> str:
        """get the cluster bound to the env, if no specific cluster is bound, return default cluster name
        this function will not check if the cluster actually exists.
        """
        wl_app = self.env.wl_app

        if wl_app.latest_config.cluster:
            return wl_app.latest_config.cluster

        ctx = AllocationContext.from_module_env(self.env)
        return ClusterAllocator(ctx).get_default().name

    def bind_cluster(self, cluster_name: Optional[str]):
        """bind `env` to cluster named `cluster_name`, if cluster_name is not given, use default cluster

        :raises: Cluster.DoesNotExist if cluster not found
        """
        wl_app = self.env.wl_app

        if cluster_name:
            cluster = Cluster.objects.get(name=cluster_name)
        else:
            ctx = AllocationContext.from_module_env(self.env)
            cluster = ClusterAllocator(ctx).get_default()

        # bind cluster to wl_app
        latest_config = wl_app.latest_config
        latest_config.cluster = cluster.name
        latest_config.mount_log_to_host = cluster.has_feature_flag(
            ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST,
        )
        latest_config.save()


def get_app_default_module_prod_env_cluster(app: "Application") -> Cluster:
    """获取默认模块生产环境应用使用的集群名称"""
    env = app.get_default_module().envs.get(environment=AppEnvironment.PRODUCTION)
    return EnvClusterService(env).get_cluster()


def get_app_default_module_clusters(app: "Application") -> Dict[str, Cluster]:
    """获取默认模块各个环境应用使用的集群"""
    return {env.environment: EnvClusterService(env).get_cluster() for env in app.get_default_module().envs.all()}


def get_app_default_module_cluster_names(app: "Application") -> Dict[str, str]:
    """获取默认模块各个环境应用使用的集群名称"""
    return {env: cluster.name for env, cluster in get_app_default_module_clusters(app).items()}


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

        if not clusters.exists():
            raise ValueError(f"cluster allocator with ctx {self.ctx} and name {cluster_name} got no cluster")

        return clusters.first()

    # 快捷方法
    get_default = partial(get, cluster_name=None)

    def _list(self) -> QuerySet[Cluster]:
        """获取集群列表"""
        if policy := ClusterAllocationPolicy.objects.filter(tenant_id=self.ctx.tenant_id).first():
            return self._policy_base_list(policy)

        return self._legacy_region_base_list()

    def _policy_base_list(self, policy: ClusterAllocationPolicy) -> QuerySet[Cluster]:
        """根据策略获取集群列表"""
        cluster_names: List[str] | None = None

        if policy.type == ClusterAllocationPolicyType.UNIFORM and policy.allocation_policy:
            # 统一分配
            cluster_names = self._get_cluster_names_from_policy(policy.allocation_policy)
        elif policy.type == ClusterAllocationPolicyType.RULE_BASED:
            # 按规则分配
            for p in policy.allocation_precedence_policies:
                if self._match_precedence_policy(p):
                    cluster_names = self._get_cluster_names_from_policy(p.policy)
        else:
            raise ValueError(f"unknown cluster allocation policy type: {policy.type}")

        if not cluster_names:
            raise ValueError(f"no cluster found for policy: {policy}")

        return Cluster.objects.filter(name__in=cluster_names)

    def _get_cluster_names_from_policy(self, policy: AllocationPolicy) -> List[str] | None:
        """根据策略获取集群名称列表"""
        if policy.env_specific:
            if not policy.env_clusters:
                raise ValueError("env_clusters is required for env_specific policy")

            return policy.env_clusters.get(self.ctx.environment)

        return policy.clusters

    def _match_precedence_policy(self, policy: AllocationPrecedencePolicy) -> bool:
        # 优先级策略最后一条一定是没有匹配规则的（else）
        if not policy.matcher:
            return True

        # 按匹配规则检查，任意不匹配的，都直接返回 False
        for key, value in policy.matcher.items():
            if key == ClusterAllocationPolicyCondType.REGION_IS:
                if self.ctx.region != value:
                    return False
            elif key == ClusterAllocationPolicyCondType.USERNAME_IN:
                usernames = [u.strip() for u in value.split(",")]
                if self.ctx.username not in usernames:
                    return False
            else:
                raise ValueError(f"unknown cluster allocation policy condition type: {key}")

        return True

    def _legacy_region_base_list(self) -> QuerySet[Cluster]:
        """按 Region 获取集群列表"""
        if not self.ctx.region:
            raise ValueError("region is required for legacy list cluster")

        return Cluster.objects.filter(region=self.ctx.region).order_by("-is_default")
