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

from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig

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
    # e2b 沙箱跑在 SandboxInstance（cube MicroVM）上，用途固定为隔离型
    ctx = AllocationContext.create_for_agent_sandbox(tenant_id, region, is_isolated=True)

    try:
        candidates = ClusterAllocator(ctx).list()
    except ValueError as exc:
        # 分配器在租户没配策略、或策略选不出集群时抛 ValueError
        raise E2BClusterUnavailable(f"no cluster allocated for tenant {tenant_id}: {exc}") from exc

    cluster = candidates.filter(e2b_config__enabled=True).first()
    if cluster is None:
        raise E2BClusterUnavailable(f"none of the allocated clusters has e2b enabled for tenant {tenant_id}")

    return cluster


def get_e2b_cluster_config(cluster_name: str) -> ClusterE2BConfig:
    """读取集群的 e2b 配置。

    :raises E2BClusterNotConfigured: 集群未登记 e2b 配置，或配置已被停用
    """
    config = ClusterE2BConfig.objects.filter(cluster__name=cluster_name, enabled=True).first()
    if config is None:
        raise E2BClusterNotConfigured(f"cluster {cluster_name} missing")

    return config
