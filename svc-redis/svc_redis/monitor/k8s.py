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
from svc_redis.monitor.utils import request_timeout
from svc_redis.resources.base.base import EnhancedApiClient
from svc_redis.resources.base.kres import KPod

logger = logging.getLogger(__name__)

# 实例 CR 名, 同时是 redis-operator 给实例 Pod 打的 app 标签值
INSTANCE_NAME = generate_redis_name()
INSTANCE_LABELS = {"app": INSTANCE_NAME}
# redis-exporter 容器的名称关键字, 由 redis-operator 注入的 sidecar 使用
EXPORTER_CONTAINER_NAME_KEYWORD = "exporter"


def list_pods(client: EnhancedApiClient, namespaces: list[str], deadline: float) -> dict[str, list]:
    """按标签批量列出各命名空间的 Pod, 返回 命名空间 -> 资源列表

    只走跨 namespace 的批量查询: 查询失败直接抛出, 由调用方把该集群的实例标记为状态缺失;
    没有 item 的命名空间保持缺失.
    """
    wanted = set(namespaces)
    # 单次请求的超时不能超过整体 deadline
    kres = KPod(client, request_timeout=request_timeout(deadline))
    # 批量操作需通过 ops_batch 调用, BaseKresource 只代理了基于名称的操作
    items = kres.ops_batch.list(labels=INSTANCE_LABELS).items

    resources: dict[str, list] = {}
    for item in items:
        if item.metadata.namespace in wanted:
            resources.setdefault(item.metadata.namespace, []).append(item)
    return resources


def is_pod_ready(pod) -> bool:
    """Pod 的 Ready condition 是否为 True; 取不到 status / conditions 时判为未就绪"""
    status = pod["status"]
    if status is None:
        return False
    for condition in status["conditions"] or []:
        if condition["type"] == "Ready":
            return condition["status"] == "True"
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
    """挑一个带 redis-exporter sidecar 的 Pod 名: 主从架构优先 master, 没有 master 时取第一个

    与 pick_instance_pod 的区别: 这里只用于读 exporter 指标, 允许在缺少 master 时回退到副本;
    实例存活判定不允许这种回退.
    """
    candidates = [pod for pod in pods if _has_exporter_container(pod)]
    if not candidates:
        return ""

    # 主从架构下, 应用连接与连接数统计都以 master 为准
    masters = [pod for pod in candidates if _is_master(pod)]
    return (masters or candidates)[0].metadata.name


def pick_instance_pod(pods: list):
    """挑选代表实例可用性的 Pod: 主从结构取 redis-role=master, 单机 (只有一个 Pod) 取该 Pod

    主从结构下没有 master 时返回 None, 不用副本冒充; 就绪状态另由 is_pod_ready 判断.
    """
    for pod in pods:
        if _is_master(pod):
            return pod
    return pods[0] if len(pods) == 1 else None


def _is_master(pod) -> bool:
    """Pod 是否为 RedisReplication 的 master"""
    labels = pod.metadata["labels"]
    return labels is not None and labels.get("redis-role") == "master"


def _has_exporter_container(pod) -> bool:
    """Pod 中是否存在由 redis-operator 注入的 redis-exporter sidecar"""
    return any(EXPORTER_CONTAINER_NAME_KEYWORD in container.name for container in pod.spec.containers)
