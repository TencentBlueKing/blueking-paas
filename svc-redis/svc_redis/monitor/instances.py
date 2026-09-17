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
- redis_instance_alive: 实例对应的 StatefulSet 副本全部就绪; 查不到该资源时该样本不产出, 不把 "采集失败" 当成 "实例不可用"
- redis_instance_memory_usage_rate: Redis `used_memory` / `maxmemory`; 未设置 maxmemory 时, 分母回退为套餐的内存上限
- redis_instance_connection_usage_rate: Redis `connected_clients` / `maxclients`
- redis_instance_oom_killed: 最近 METRIC_OOM_KILLED_WINDOW 秒内是否因内存被杀死, 超过时间窗自动回到 0
- redis_instance_exporter_up: 实例有 exporter 且取数成功为 1, 取数失败为 0; 没有 exporter 的实例不产出

取不到的指标显式缺失, 不得用 0 冒充健康; 单个实例取数失败不影响其余实例出数.
"""

import json
import logging
import time
from collections import defaultdict

from django.conf import settings
from kubernetes.utils.quantity import parse_quantity
from paas_service.models import ServiceInstance, ServiceInstanceConfig

from svc_redis.monitor import exporter, k8s
from svc_redis.monitor.entities import RedisInstance, RedisInstanceStatus
from svc_redis.monitor.utils import collect_deadline, map_concurrently
from svc_redis.resources.base.base import EnhancedApiClient, get_client_by_cluster_name

logger = logging.getLogger(__name__)

# 实例 ID -> (该实例所在集群的 k8s client, exporter Pod 名)
ExporterTargets = dict[str, tuple[EnhancedApiClient, str]]

# 上次采集的结果与时间(monotonic 秒); 取结果的一方只读, 不得修改
_cache: tuple[float, list[RedisInstanceStatus]] | None = None


def collect_instance_statuses() -> list[RedisInstanceStatus]:
    """采集全部已分配 (未回收) 实例的运行状态; METRIC_COLLECT_CACHE_TTL 秒内复用上次结果"""
    global _cache

    started_at = time.monotonic()
    if _cache is not None and started_at - _cache[0] < settings.METRIC_COLLECT_CACHE_TTL:
        return _cache[1]

    # k8s 与 exporter 的查询共用这一份 deadline
    deadline = collect_deadline()

    statuses: list[RedisInstanceStatus] = []
    # 套餐内存上限: Redis 未设置 maxmemory 时的内存使用率分母
    memory_limits: dict[str, int | None] = {}
    for instance, memory_limit in _list_allocated_instances():
        statuses.append(RedisInstanceStatus(instance))
        memory_limits[instance.bk_instance] = memory_limit

    exporter_targets = _fill_k8s_states(statuses, deadline)
    _fill_usage_rates(statuses, exporter_targets, memory_limits, deadline)

    _cache = (started_at, statuses)
    return statuses


def _list_allocated_instances() -> list[tuple[RedisInstance, int | None]]:
    """全部已分配(未回收)实例及其套餐内存上限; 单个实例解析失败只跳过自己"""
    # credentials 是加密字段, 读取即解密; 采集用不到它, 使用 only() 显式排除
    rows = list(
        ServiceInstance.objects.filter(to_be_deleted=False)
        .select_related("plan")
        .only("uuid", "config", "plan_id", "plan__config")
    )
    app_infos = {
        str(config.instance_id): config.paas_app_info
        for config in ServiceInstanceConfig.objects.filter(instance_id__in=[row.uuid for row in rows]).only(
            "instance_id", "paas_app_info"
        )
    }

    items = []
    for row in rows:
        try:
            instance, memory_limit = _build_instance(row, app_infos.get(str(row.uuid)) or {})
        except Exception:
            logger.exception("unable to build the redis instance<%s>", row.uuid)
            continue
        if instance is not None:
            items.append((instance, memory_limit))
    return items


def _build_instance(service_instance: ServiceInstance, app_info: dict) -> tuple[RedisInstance | None, int | None]:
    """由平台分配记录构建实例身份与套餐内存上限, 无法解析的实例 (如 client-side 实例) 返回 (None, None)"""
    if service_instance.plan is None:
        logger.warning("skip client-side redis instance<%s> which has no plan", service_instance.uuid)
        return None, None

    plan_config = json.loads(service_instance.plan.config or "{}")
    # 未开启 monitor 的套餐创建的实例没有 redis-exporter, 采集不到 exporter 指标, 不纳入监控
    if not plan_config.get("monitor"):
        logger.debug("skip redis instance<%s> whose plan has monitor disabled", service_instance.uuid)
        return None, None

    cluster_name = plan_config.get("cluster_name")
    if not cluster_name:
        logger.warning("no cluster_name found in plan config of redis instance<%s>", service_instance.uuid)
        return None, None

    return (
        RedisInstance(
            bk_instance=str(service_instance.uuid),
            bk_cluster=str(cluster_name),
            namespace=str(service_instance.config.get("namespace") or ""),
            bk_app_code=str(app_info.get("app_code", "")),
            bk_module=str(app_info.get("module", "")),
            bk_env=str(app_info.get("environment", "")),
        ),
        _parse_memory_size(plan_config.get("memory_size")),
    )


def _parse_memory_size(memory_size) -> int | None:
    """将套餐中的内存上限 (如 "2Gi") 解析为字节数"""
    if not memory_size:
        return None

    try:
        return int(parse_quantity(str(memory_size)))
    except (ValueError, TypeError):
        logger.warning("unable to parse memory size: %s", memory_size)
        return None


def _fill_k8s_states(statuses: list[RedisInstanceStatus], deadline: float) -> ExporterTargets:
    """填充存活与 OOMKilled, 并找出可读取 exporter 指标的 Pod

    每个集群一个并发任务, 共用本次采集的 deadline; 单个集群失败只影响该集群的实例.
    只有命名空间查询成功时才写回字段: 查不到同名 StatefulSet 判为不可用, 查询失败则保持缺失.
    """
    statuses_by_cluster: dict[str, list[RedisInstanceStatus]] = defaultdict(list)
    for status in statuses:
        statuses_by_cluster[status.instance.bk_cluster].append(status)

    clients: dict[str, EnhancedApiClient] = {}
    for cluster_name in statuses_by_cluster:
        try:
            clients[cluster_name] = get_client_by_cluster_name(cluster_name)
        except Exception:
            logger.exception("unable to init k8s client of cluster<%s>", cluster_name)

    def _list_cluster_resources(cluster_name: str):
        client = clients[cluster_name]
        cluster_statuses = statuses_by_cluster[cluster_name]
        namespaces = [status.instance.namespace for status in cluster_statuses if status.instance.namespace]
        try:
            statefulsets = k8s.list_statefulsets(client, namespaces, deadline)
            pods = k8s.list_pods(client, namespaces, deadline)
        except Exception:
            logger.exception("unable to collect k8s states of cluster<%s>", cluster_name)
            return None
        return cluster_name, statefulsets, pods

    exporter_targets: ExporterTargets = {}
    for resources in map_concurrently(_list_cluster_resources, list(clients), deadline):
        if resources is None:
            continue

        cluster_name, statefulsets, pods = resources
        for status in statuses_by_cluster[cluster_name]:
            pod_name = _fill_instance_state(status, statefulsets, pods)
            if pod_name:
                exporter_targets[status.instance.bk_instance] = (clients[cluster_name], pod_name)

    return exporter_targets


def _fill_instance_state(status: RedisInstanceStatus, statefulsets: dict[str, list], pods: dict[str, list]) -> str:
    """写回单个实例的存活 / OOMKilled, 返回可读取 exporter 指标的 Pod 名 (没有则返回空字符串)"""
    namespace = status.instance.namespace
    sts_list = statefulsets.get(namespace)
    pods_list = pods.get(namespace)
    # 命名空间不在结果里 = 该命名空间查询失败, 字段保持缺失;
    # 在结果里但查不到同名 StatefulSet = 资源确实不存在, 判为不可用
    status.alive = k8s.is_instance_ready(sts_list) if sts_list is not None else None
    if not pods_list:
        return ""

    status.oom_killed = any(k8s.pod_was_oom_killed(pod) for pod in pods_list)
    return k8s.pick_exporter_pod_name(pods_list)


def _fill_usage_rates(
    statuses: list[RedisInstanceStatus],
    exporter_targets: ExporterTargets,
    memory_limits: dict[str, int | None],
    deadline: float,
) -> None:
    """并发读取内存/连接使用率, 取不到的指标保持缺失

    exporter_up 只在实例确实有 exporter 时产出: 取数成功为 1, 失败为 0;
    没有 exporter (monitor 未开启) 或 k8s 查询失败的实例不产出该样本, 以区别于取数失败.
    """
    fetchable = [status for status in statuses if status.instance.bk_instance in exporter_targets]

    def _fetch(status: RedisInstanceStatus):
        client, pod_name = exporter_targets[status.instance.bk_instance]
        return status, exporter.fetch_usage(status.instance, client, pod_name, deadline)

    for status, usage in map_concurrently(_fetch, fetchable, deadline):
        status.exporter_up = usage is not None
        if usage is None:
            continue

        # 未设置 maxmemory (值为 0) 时, 使用率分母回退为套餐的内存上限
        memory_limit = usage.maxmemory or memory_limits.get(status.instance.bk_instance)
        if usage.used_memory is not None and memory_limit:
            status.memory_usage_rate = usage.used_memory / memory_limit
        if usage.connected_clients is not None and usage.maxclients:
            status.connection_usage_rate = usage.connected_clients / usage.maxclients
