# -*- coding: utf-8 -*-
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
from collections.abc import Iterable

from django.db.models import QuerySet

from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.constants import ClusterUsage
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate

from .constants import E2BSandboxStatus
from .exceptions import E2BClusterNotConfigured, E2BClusterUnavailable

logger = logging.getLogger(__name__)


def select_e2b_cluster(tenant_id: str, region: str | None = None) -> Cluster:
    """为新沙箱挑一个集群。

    复用平台的集群分配器，再交上「已登记且启用 e2b 配置」这个条件。分配器是策略求值器
    而非绑定表，同样的入参在策略调整或首选集群不可用时结果会变。

    :param tenant_id: 归属应用的租户
    :param region: 归属应用的 region，缺省时由分配上下文取平台默认值
    :raises E2BClusterUnavailable: 没有既被策略选中、又启用了 e2b 配置的集群
    """
    cluster = list_e2b_clusters(tenant_id, region).first()
    if cluster is None:
        raise E2BClusterUnavailable(f"none of the allocated clusters has e2b enabled for tenant {tenant_id}")

    return cluster


def list_e2b_clusters(tenant_id: str, region: str | None = None) -> QuerySet[Cluster]:
    """列出可分配给该租户、且启用了 e2b 配置的集群，按分配器的优先级排列。

    :raises E2BClusterUnavailable: 租户没配分配策略，或策略选不出集群
    """
    # e2b 沙箱用独立的用途，与平台自有的 SandboxInstance 沙箱分开调度
    ctx = AllocationContext.create_for_agent_sandbox(tenant_id, region, usage=ClusterUsage.AGENT_SANDBOX_E2B)

    try:
        candidates = ClusterAllocator(ctx).list()
    except ValueError as exc:
        # 分配器在租户没配策略、或策略选不出集群时抛 ValueError
        raise E2BClusterUnavailable(f"no cluster allocated for tenant {tenant_id}: {exc}") from exc

    return candidates.filter(e2b_config__enabled=True)


def get_e2b_cluster_config(cluster_name: str) -> ClusterE2BConfig:
    """读取集群的 e2b 配置。

    停用的配置同样返回：enabled 只决定新沙箱是否调度到该集群，存量沙箱的续期、销毁、
    对账仍要经它访问网关，否则集群停用后存量沙箱无法收敛，配置也就永远删不掉。

    :raises E2BClusterNotConfigured: 集群未登记 e2b 配置
    """
    # 监控指标需要集群名做标签
    config = ClusterE2BConfig.objects.select_related("cluster").filter(cluster__name=cluster_name).first()
    if config is None:
        raise E2BClusterNotConfigured(f"cluster {cluster_name} missing")

    return config


def list_enabled_e2b_configs() -> list[ClusterE2BConfig]:
    return list(ClusterE2BConfig.objects.select_related("cluster").filter(enabled=True))


def list_enabled_e2b_cluster_names() -> set[str]:
    return set(ClusterE2BConfig.objects.filter(enabled=True).values_list("cluster__name", flat=True))


def resolve_template_targets(
    templates: Iterable[E2BSandboxTemplate], enabled_e2b_clusters: set[str] | None = None
) -> dict[str, set[str]]:
    """求各模板应当下发到的集群，键为资源名。

    内置模板是全部启用 e2b 的集群，自定义模板只到应用租户可分配的集群，同一（租户, region）只做一次集群分配。

    :param enabled_e2b_clusters: 启用 e2b 的集群名，不传则查库。调用方还要按同一份集群遍历时须传入，
        否则两次查询之间集群可能有变化
    """
    if enabled_e2b_clusters is None:
        enabled_e2b_clusters = list_enabled_e2b_cluster_names()

    # 缓存(租户, region)到分配集群的映射，避免重复查询
    allocated: dict[tuple[str, str], set[str]] = {}
    targets = {}
    for template in templates:
        # 内置模板需要下发到所有集群
        if template.is_builtin:
            targets[template.resource_name] = enabled_e2b_clusters
            continue

        app = template.application
        key = (app.tenant_id, app.region)
        if key not in allocated:
            try:
                allocated[key] = set(list_e2b_clusters(app.tenant_id, app.region).values_list("name", flat=True))
            except E2BClusterUnavailable:
                logger.warning("no e2b cluster allocated for tenant %s, skip its custom templates", app.tenant_id)
                allocated[key] = set()
        targets[template.resource_name] = allocated[key] & enabled_e2b_clusters
    return targets


def count_live_sandboxes(cluster_name: str) -> int:
    """统计集群上仍占用底层资源的沙箱数量。

    这些沙箱的后续操作（续期、销毁、对账）都要经该集群的 e2b 配置访问网关，
    移除配置前需要确认数量为 0，否则它们会变成平台无法回收的孤儿。
    """
    return E2BSandbox.objects.filter(cluster_name=cluster_name, status__in=E2BSandboxStatus.active_values()).count()
