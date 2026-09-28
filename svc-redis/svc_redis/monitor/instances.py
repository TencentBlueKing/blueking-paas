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

"""已分配实例的采集编排

只采集开启 monitor 的套餐创建的实例, 这类实例才有 redis-exporter sidecar.

指标:
- redis_instance_alive: 代表 Pod (主从的 master / 单机的唯一 Pod) 已就绪; 副本未就绪不影响; 查询失败时该样本不产出, 不把 "采集失败" 当成 "实例不可用"
- redis_instance_memory_usage_rate: Redis `used_memory` / `maxmemory`; 未设置 maxmemory 时, 分母回退为套餐的内存上限
- redis_instance_connection_usage_rate: Redis `connected_clients` / `maxclients`
- redis_instance_oom_killed: 最近 METRIC_OOM_KILLED_WINDOW 秒内是否因内存被杀死, 超过时间窗自动回到 0
- redis_instance_exporter_up: 实例有 exporter 且取数成功为 1, 取数失败为 0; 没有 exporter 的实例不产出
- redis_instance_db_keys: 实例所有 DB 的 key 总数 (redis_db_keys 按 db 标签求和)

采集分三个阶段: 实例清单 (DB) -> Pod 状态 (k8s) -> 用量 (exporter), 结果写入多 worker / 副本共享的缓存.

取不到的指标显式缺失, 不得用 0 冒充健康; 单个实例取数失败不影响其余实例出数.
"""

import logging
from collections import defaultdict
from typing import NamedTuple

from django.conf import settings
from django.core.cache import cache

from svc_redis.monitor import exporter, k8s
from svc_redis.monitor.entities import RedisInstanceStatus
from svc_redis.monitor.inventory import list_allocated_instances
from svc_redis.monitor.utils import collect_deadline, map_with_deadline
from svc_redis.resources.base.base import EnhancedApiClient, clone_client, get_client_by_cluster_name

logger = logging.getLogger(__name__)


class ExporterTarget(NamedTuple):
    """exporter 取数目标: 实例所在集群的 k8s client + 目标 Pod 名"""

    client: EnhancedApiClient
    pod_name: str


# 实例 ID -> exporter 取数目标
ExporterTargets = dict[str, ExporterTarget]

# 采集结果的缓存 key: 结果存放在数据库缓存里, 由全部 worker / 副本共享
_STATUSES_CACHE_KEY = "svc_redis:monitor:instance_statuses"


def collect_instance_statuses() -> list[RedisInstanceStatus]:
    """采集全部已分配 (未回收) 实例的运行状态; METRIC_COLLECT_CACHE_TTL 秒内复用上次结果

    采集分三个阶段: 实例清单 -> Pod 状态 -> 用量; 结果写入多 worker / 副本共享的缓存.
    """
    ttl = settings.METRIC_COLLECT_CACHE_TTL
    if ttl > 0:
        cached = cache.get(_STATUSES_CACHE_KEY)
        if cached is not None:
            return [RedisInstanceStatus.from_dict(data) for data in cached]

    # k8s 与 exporter 的查询共用这一份 deadline
    deadline = collect_deadline()

    statuses: list[RedisInstanceStatus] = []
    # 套餐内存上限: Redis 未设置 maxmemory 时的内存使用率分母
    memory_limits: dict[str, int | None] = {}
    for allocated in list_allocated_instances():
        statuses.append(RedisInstanceStatus(allocated.instance))
        memory_limits[allocated.instance.bk_instance] = allocated.memory_limit

    exporter_targets = _collect_k8s_states(statuses, deadline)
    _collect_usage(statuses, exporter_targets, memory_limits, deadline)

    if ttl > 0:
        cache.set(_STATUSES_CACHE_KEY, [status.as_dict() for status in statuses], ttl)
    return statuses


def _collect_k8s_states(statuses: list[RedisInstanceStatus], deadline: float) -> ExporterTargets:
    """采集各实例所在集群的 Pod 状态, 写回存活 / OOMKilled, 并选出 exporter 取数目标

    每个集群一个并发任务, 共用本次采集的 deadline; 单个集群失败只影响该集群的实例.
    查询失败时字段保持缺失并标记 k8s_state_missing; 代表 Pod 缺失 (如主从缺 master) 判为不可用.
    """
    statuses_by_cluster: dict[str, list[RedisInstanceStatus]] = defaultdict(list)
    for status in statuses:
        statuses_by_cluster[status.instance.bk_cluster].append(status)

    clients = _init_cluster_clients(list(statuses_by_cluster))

    def _list_cluster_pods(cluster_name: str):
        namespaces = [s.instance.namespace for s in statuses_by_cluster[cluster_name] if s.instance.namespace]
        try:
            return cluster_name, k8s.list_pods(clients[cluster_name], namespaces, deadline)
        except Exception:
            logger.exception("unable to collect k8s states of cluster<%s>", cluster_name)
            return None

    exporter_targets: ExporterTargets = {}
    collected_clusters: set[str] = set()
    for result in map_with_deadline(_list_cluster_pods, list(clients), deadline):
        if result is None:
            continue

        cluster_name, pods = result
        collected_clusters.add(cluster_name)
        for status in statuses_by_cluster[cluster_name]:
            pods_list = pods.get(status.instance.namespace)
            _apply_pod_state(status, pods_list)

            pod_name = k8s.pick_exporter_pod_name(pods_list or [])
            if pod_name:
                exporter_targets[status.instance.bk_instance] = ExporterTarget(clients[cluster_name], pod_name)

    _mark_missing_clusters(statuses_by_cluster, collected_clusters)
    return exporter_targets


def _init_cluster_clients(cluster_names: list[str]) -> dict[str, EnhancedApiClient]:
    """初始化各集群的 k8s client; 单个集群失败只记录日志, 其下实例随后会被标记为状态缺失"""
    clients: dict[str, EnhancedApiClient] = {}
    for cluster_name in cluster_names:
        try:
            clients[cluster_name] = get_client_by_cluster_name(cluster_name)
        except Exception:
            logger.exception("unable to init k8s client of cluster<%s>", cluster_name)
    return clients


def _apply_pod_state(status: RedisInstanceStatus, pods_list: list | None) -> None:
    """写回单个实例的存活 / OOMKilled

    存活只看代表 Pod (主从的 master / 单机的唯一 Pod): 副本未就绪不影响实例可用;
    pods_list 为 None (命名空间不在查询结果里) 表示查询失败, 字段保持缺失并标记 k8s_state_missing.
    """
    if pods_list is None:
        status.k8s_state_missing = True
        return

    pod = k8s.pick_instance_pod(pods_list)
    status.alive = pod is not None and k8s.is_pod_ready(pod)
    if not pods_list:
        return

    status.oom_killed = any(k8s.pod_was_oom_killed(item) for item in pods_list)


def _mark_missing_clusters(
    statuses_by_cluster: dict[str, list[RedisInstanceStatus]], collected_clusters: set[str]
) -> None:
    """未被采集到的集群 (初始化失败 / 查询异常 / deadline 放弃): 其下实例标记状态缺失"""
    for cluster_name, cluster_statuses in statuses_by_cluster.items():
        if cluster_name in collected_clusters:
            continue
        for status in cluster_statuses:
            status.k8s_state_missing = True


def _collect_usage(
    statuses: list[RedisInstanceStatus],
    exporter_targets: ExporterTargets,
    memory_limits: dict[str, int | None],
    deadline: float,
) -> None:
    """并发读取 exporter 指标, 回填 exporter_up / 内存与连接使用率 / db_keys

    exporter_up 只在实例确实有 exporter 时产出: 取数成功为 1, 失败为 0;
    没有 exporter (monitor 未开启) 或 k8s 查询失败的实例不产出该样本, 以区别于取数失败.
    """
    fetchable = [status for status in statuses if status.instance.bk_instance in exporter_targets]

    def _fetch(status: RedisInstanceStatus):
        target = exporter_targets[status.instance.bk_instance]
        # 每个任务独享一个克隆出来的 client; worker 只取数, status 一律由主线程回填
        return status, exporter.fetch_usage(status.instance, clone_client(target.client), target.pod_name, deadline)

    for status, usage in map_with_deadline(_fetch, fetchable, deadline):
        status.exporter_up = usage is not None
        if usage is None:
            continue

        status.db_keys = usage.db_keys

        # 未设置 maxmemory (值为 0) 时, 使用率分母回退为套餐的内存上限
        limit = usage.maxmemory or memory_limits.get(status.instance.bk_instance)
        if usage.used_memory is not None and limit:
            status.memory_usage_rate = usage.used_memory / limit
        if usage.connected_clients is not None and usage.maxclients:
            status.connection_usage_rate = usage.connected_clients / usage.maxclients

    # 有 exporter 但结果未被回填 (deadline 截断 / 任务异常): 按取数失败处理, 避免与 "没有 exporter" 混淆
    for status in fetchable:
        if status.exporter_up is None:
            status.exporter_up = False
            status.usage_fetch_skipped = True
