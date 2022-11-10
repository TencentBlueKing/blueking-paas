# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
import time
import typing

from prometheus_client import REGISTRY, Gauge
from prometheus_client.core import GaugeMetricFamily

from . import tasks
from .scheduler import Scheduler
from .tasks import (
    CheckClusterAlive,
    CheckInstanceAlive,
    CheckInstanceDLXQueueStatus,
    CheckInstanceLimits,
    CheckInstanceQueueStatus,
    CronCheckInstanceConnectionStatus,
)

logger = logging.getLogger(__name__)


class FunctionCollector:
    collect_duration_metric = Gauge(
        "monitor_task_collect_duration_seconds",
        "duration to collect monitor task metrics",
        ["name"],
    )

    def __init__(self, func):
        self.func = func
        self.name = func.__name__

    def collect(self):
        start_at = time.time()

        try:
            yield from self.func()
        except Exception:
            logger.exception("get metrics failed")

        end_at = time.time()
        self.collect_duration_metric.labels(self.name).set(end_at - start_at)


@FunctionCollector
def worker_stats_collector():
    info = GaugeMetricFamily("worker_cluster_info", "worker cluster info", labels=["worker", "name"])

    try:
        scheduler = Scheduler.get()
    except RuntimeError:
        return

    uuid = scheduler.uuid
    stats = scheduler.stats()
    for k, v in stats.items():
        info.add_metric([uuid, k], v)

    yield info


@FunctionCollector
def rabbit_cluster_collector():
    alive = GaugeMetricFamily(
        "rabbitmq_cluster_alive",
        "rabbitmq cluster alive status",
        labels=CheckClusterAlive.Result.as_label_keys() + ["name"],
    )
    results: 'typing.Dict[str, CheckClusterAlive.Result]' = tasks.cluster_alive.get_cron_result() or {}
    for name, result in results.items():
        if result is None or result.ok is None:
            value = -1
        elif result.ok:
            value = 1
        else:
            value = 0
        alive.add_metric(result.as_label_values() + [name], value)
    yield alive


@FunctionCollector
def instance_alive_collector():
    alive = GaugeMetricFamily(
        "rabbitmq_instance_alive", "rabbitmq instance alive status", labels=CheckInstanceAlive.Result.as_label_keys()
    )
    results: 'typing.Dict[str, CheckInstanceAlive.Result]' = tasks.instance_alive.get_cron_result() or {}
    for instance, result in results.items():
        if result is None or result.ok is None:
            value = -1
        elif result.ok:
            value = 1
        else:
            value = 0
        alive.add_metric(result.as_label_values(), value)
    yield alive


@FunctionCollector
def instance_queue_collector():
    queues = GaugeMetricFamily(
        "rabbitmq_instance_queues",
        "rabbitmq instance queue totals",
        labels=CheckInstanceQueueStatus.Result.as_label_keys(),
    )
    usage = GaugeMetricFamily(
        "rabbitmq_instance_queue_usage",
        "percentage of queue usage",
        labels=CheckInstanceQueueStatus.Result.as_label_keys() + ["queue"],
    )
    consumers = GaugeMetricFamily(
        "rabbitmq_instance_queue_consumers",
        "consumers of queue",
        labels=CheckInstanceQueueStatus.Result.as_label_keys() + ["queue"],
    )
    messages = GaugeMetricFamily(
        "rabbitmq_instance_queue_messages",
        "messages of queue",
        labels=CheckInstanceQueueStatus.Result.as_label_keys() + ["queue"],
    )
    messages_size = GaugeMetricFamily(
        "rabbitmq_instance_queue_message_bytes",
        "messages size of queue",
        labels=CheckInstanceQueueStatus.Result.as_label_keys() + ["queue"],
    )

    results: 'typing.Dict[str, CheckInstanceQueueStatus.Result]' = tasks.instance_queue.get_cron_result() or {}
    for instance, result in results.items():
        labels = result.as_label_values()
        queues.add_metric(labels, len(result.queues))

        for queue in result.queues:
            usage.add_metric(labels + [queue.name], queue.messages / queue.max_length)
            consumers.add_metric(labels + [queue.name], queue.consumers)
            messages.add_metric(labels + [queue.name], queue.messages)
            messages_size.add_metric(labels + [queue.name], queue.message_bytes)

    yield queues
    yield usage
    yield consumers
    yield messages
    yield messages_size


@FunctionCollector
def instance_dlx_queue_collector():
    messages = GaugeMetricFamily(
        "rabbitmq_instance_dlx_queue_messages",
        "messages of queue",
        labels=CheckInstanceDLXQueueStatus.Result.as_label_keys() + ["queue"],
    )

    results: 'typing.Dict[str, CheckInstanceDLXQueueStatus.Result]' = tasks.instance_dlx_queue.get_cron_result() or {}
    for instance, result in results.items():
        if result is None:
            logger.debug("dlx queue of instance %s not found, skipped", instance)
            continue

        messages.add_metric(result.as_label_values() + [result.status.name], result.status.messages)

    yield messages


@FunctionCollector
def instance_connections_collector():
    connections = GaugeMetricFamily(
        "rabbitmq_instance_connections",
        "connections of vhost",
        labels=CronCheckInstanceConnectionStatus.ConnectionStatus.as_label_keys() + ["state"],
    )

    results: 'typing.Dict[str, CronCheckInstanceConnectionStatus.ConnectionStatus]'
    results = tasks.connection_status.get_cron_result() or {}
    for instance, result in results.items():
        labels = result.as_label_values()
        connections.add_metric(labels + ["running"], result.running)
        connections.add_metric(labels + ["idle"], result.idle)
        connections.add_metric(labels + ["blocking"], result.blocking)
        connections.add_metric(labels + ["blocked"], result.blocked)
        connections.add_metric(labels + ["others"], result.others)

    yield connections


@FunctionCollector
def instance_limit_policy_collector():
    limits = GaugeMetricFamily(
        "rabbitmq_instance_limits", "limits of vhost", labels=CheckInstanceLimits.Result.as_label_keys() + ["resource"]
    )
    results: 'typing.Dict[str, CheckInstanceLimits.Result]' = tasks.instance_limits.get_cron_result() or {}
    for instance, result in results.items():
        if not result:
            continue
        labels = result.as_label_values()
        limits.add_metric(labels + ["queue"], result.queues)
        limits.add_metric(labels + ["connection"], result.connections)

    yield limits


def ready():
    REGISTRY.register(worker_stats_collector)
    REGISTRY.register(rabbit_cluster_collector)
    REGISTRY.register(instance_alive_collector)
    REGISTRY.register(instance_queue_collector)
    REGISTRY.register(instance_dlx_queue_collector)
    REGISTRY.register(instance_connections_collector)
    REGISTRY.register(instance_limit_policy_collector)
