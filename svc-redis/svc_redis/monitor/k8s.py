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

"""实例资源与 Pod 状态的查询

k8s 资源由 kres 的动态客户端封装(见 resources/base/kube_client.py): 必需字段用 resource.field 访问,
缺失会抛 AttributeError; 可选字段用 resource["field"] 访问, 缺失返回 None. 下面按这个约定区分,
不用 getattr 兜底.

所有查询共用一个 deadline: 单次请求超时取 min(METRIC_COLLECT_REQUEST_TIMEOUT, 剩余时间).
"""

import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.utils.timezone import now

from svc_redis.controller.manifests import generate_redis_name
from svc_redis.monitor.utils import map_concurrently, request_timeout
from svc_redis.resources.base.base import clone_client
from svc_redis.resources.base.kres import KPod, KStatefulSet

logger = logging.getLogger(__name__)

# 实例资源 (StatefulSet/Pod) 的名字与标签, 由 redis-operator 注入
INSTANCE_NAME = generate_redis_name()
INSTANCE_LABELS = {"app": INSTANCE_NAME}
# redis-exporter 容器的名称关键字, 由 redis-operator 注入的 sidecar 使用
EXPORTER_CONTAINER_NAME_KEYWORD = "exporter"


def list_statefulsets(client, namespaces: list[str], deadline: float) -> dict[str, list]:
    """列出各命名空间的 StatefulSet, 返回 命名空间 -> 资源列表"""
    return _list_resources(KStatefulSet, client, namespaces, deadline)


def list_pods(client, namespaces: list[str], deadline: float) -> dict[str, list]:
    """列出各命名空间的 Pod, 返回 命名空间 -> 资源列表"""
    return _list_resources(KPod, client, namespaces, deadline)


def _list_resources(kres_cls, client, namespaces: list[str], deadline: float) -> dict[str, list]:
    """按标签批量列出资源, 返回 命名空间 -> 资源列表"""
    namespaces = set(namespaces)
    # 单次请求的超时不能超过整体 deadline
    kres = kres_cls(client, request_timeout=request_timeout(deadline))

    try:
        # 批量操作需通过 ops_batch 调用, BaseKresource 只代理了基于名称的操作
        items = kres.ops_batch.list(labels=INSTANCE_LABELS).items
    except Exception:
        logger.warning(
            "unable to batch list %s by label, fallback to per-namespace list", kres_cls.kind, exc_info=True
        )
        return _list_by_namespace(kres_cls, client, list(namespaces), deadline)

    # 按实际返回的 item 聚合: 没有 item 的命名空间保持缺席(缺失)
    resources: dict[str, list] = {}
    for item in items:
        if item.metadata.namespace in namespaces:
            resources.setdefault(item.metadata.namespace, []).append(item)
    return resources


def _list_by_namespace(kres_cls, client, namespaces: list[str], deadline: float) -> dict[str, list]:
    """逐个命名空间并发查询

    查询失败的命名空间不出现在结果里(判为缺失)
    查询成功但结果为空列表时保留空列表: 这是逐 namespace 确认过的 "确实没有资源", 判为不可用.

    每个任务克隆 client 并重建 kres.
    """

    def _list(namespace: str):
        try:
            kres = kres_cls(clone_client(client), request_timeout=request_timeout(deadline))
            return namespace, kres.ops_batch.list(labels=INSTANCE_LABELS, namespace=namespace).items
        except Exception:
            logger.exception("unable to list %s in namespace<%s>", kres_cls.kind, namespace)
            return namespace, None

    return {
        namespace: items for namespace, items in map_concurrently(_list, namespaces, deadline) if items is not None
    }


def is_instance_ready(statefulsets: list) -> bool:
    """实例对应的 StatefulSet 是否全部就绪"""
    for statefulset in statefulsets:
        if statefulset.metadata.name != INSTANCE_NAME:
            continue
        status = statefulset["status"]
        if status is None:
            return False
        replicas = status["replicas"] or 0
        ready_replicas = status["readyReplicas"] or 0
        return replicas > 0 and replicas == ready_replicas

    return False


def pod_was_oom_killed(pod) -> bool:
    """Pod 是否在最近 METRIC_OOM_KILLED_WINDOW 秒内因 OOM 被杀死"""
    killed_at = _last_oom_killed_at(pod)
    if killed_at is None:
        return False
    return now() - killed_at <= timedelta(seconds=settings.METRIC_OOM_KILLED_WINDOW)


def _last_oom_killed_at(pod) -> datetime | None:
    """Pod 中最近一次因 OOMKilled 终止的时间, 没有则返回 None"""
    status = pod["status"]
    if status is None:
        return None

    timestamps = []
    for container_status in status["containerStatuses"] or []:
        # state / lastState 未必存在, terminated 只在容器被终止后才出现
        for state in (container_status["state"], container_status["lastState"]):
            terminated = state["terminated"] if state is not None else None
            if terminated is None or terminated["reason"] != "OOMKilled":
                continue
            finished_at = _parse_k8s_time(terminated["finishedAt"])
            if finished_at:
                timestamps.append(finished_at)
    return max(timestamps, default=None)


def _parse_k8s_time(value: str | None) -> datetime | None:
    """解析 k8s 的 RFC3339 时间; 取不到或格式非法时返回 None"""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        logger.warning("unable to parse k8s time: %s", value)
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def pick_exporter_pod_name(pods: list) -> str:
    """挑选一个带 redis-exporter sidecar 的 Pod: 主从架构优先 master, 否则取第一个"""
    candidates = [pod for pod in pods if _has_exporter_container(pod)]
    if not candidates:
        return ""

    # 主从架构下, 应用连接与连接数统计都以 master 为准
    return max(candidates, key=_is_master).metadata.name


def _is_master(pod) -> bool:
    """Pod 是否为 RedisReplication 的 master"""
    labels = pod.metadata["labels"]
    return labels is not None and labels.get("redis-role") == "master"


def _has_exporter_container(pod) -> bool:
    """Pod 中是否存在由 redis-operator 注入的 redis-exporter sidecar"""
    return any(EXPORTER_CONTAINER_NAME_KEYWORD in container.name for container in pod.spec.containers)
