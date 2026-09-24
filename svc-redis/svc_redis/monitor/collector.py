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

"""把采集结果转换为 prometheus 指标"""

import logging

from prometheus_client.core import CollectorRegistry, GaugeMetricFamily

from svc_redis.monitor.entities import RedisInstance, RedisInstanceStatus
from svc_redis.monitor.instances import collect_instance_statuses

logger = logging.getLogger(__name__)


class RedisInstanceMetricsCollector:
    """采集全部已分配 Redis 实例的指标"""

    def collect(self):
        success = True
        try:
            statuses = collect_instance_statuses()
        except Exception:
            # 采集异常不能让整个 /metrics 挂掉, 只返回空的实例指标;
            # 指标构建本身的错误不属于这里, 必须暴露出来
            logger.exception("unable to collect redis instance metrics")
            statuses = []
            success = False

        k8s_missing = any(status.k8s_state_missing for status in statuses)
        usage_skipped = any(status.usage_fetch_skipped for status in statuses)
        collect_success = int(success and not k8s_missing and not usage_skipped)

        success_family, instances_family = self._build_self_families()
        success_family.add_metric([], collect_success)
        instances_family.add_metric([], len(statuses))

        yield from self._build_families(statuses)
        yield success_family
        yield instances_family

    def describe(self):
        """prometheus_client 注册时会调用, 返回空指标以避免触发真实采集"""
        yield from self._build_families([])
        yield from self._build_self_families()

    @staticmethod
    def _build_families(statuses: list[RedisInstanceStatus]) -> list[GaugeMetricFamily]:
        labels = RedisInstance.as_label_keys()
        alive = GaugeMetricFamily("redis_instance_alive", "whether the redis instance is available", labels=labels)
        oom_killed = GaugeMetricFamily(
            "redis_instance_oom_killed", "whether the redis container was oom killed", labels=labels
        )
        exporter_up = GaugeMetricFamily(
            "redis_instance_exporter_up",
            "whether the redis exporter metrics were collected; absent when the instance has no exporter",
            labels=labels,
        )
        memory_usage = GaugeMetricFamily(
            "redis_instance_memory_usage_rate", "memory usage rate of the redis instance", labels=labels
        )
        connection_usage = GaugeMetricFamily(
            "redis_instance_connection_usage_rate", "connection usage rate of the redis instance", labels=labels
        )
        db_keys = GaugeMetricFamily(
            "redis_instance_db_keys", "total number of keys across all DBs of the redis instance", labels=labels
        )

        for status in statuses:
            label_values = status.instance.as_label_values()
            _add_if_present(alive, label_values, status.alive)
            _add_if_present(oom_killed, label_values, status.oom_killed)
            _add_if_present(exporter_up, label_values, status.exporter_up)
            _add_if_present(memory_usage, label_values, status.memory_usage_rate)
            _add_if_present(connection_usage, label_values, status.connection_usage_rate)
            _add_if_present(db_keys, label_values, status.db_keys)

        return [alive, oom_killed, exporter_up, memory_usage, connection_usage, db_keys]

    @staticmethod
    def _build_self_families() -> list[GaugeMetricFamily]:
        """采集链路的自监控: 采集器是否健康 / 应采集实例数"""
        success_family = GaugeMetricFamily(
            "redis_instance_collect_success",
            "whether the metric collection pipeline is healthy; target-side failures are not counted",
        )
        instances_family = GaugeMetricFamily(
            "redis_instance_collect_instances", "number of instances that should be collected"
        )

        return [success_family, instances_family]


def _add_if_present(family: GaugeMetricFamily, labels: list[str], value: float | None):
    """取不到的值不产出样本 (显式缺失), 不用 0 冒充; gauge 值统一转 float"""
    if value is not None:
        family.add_metric(labels, value)


metrics_collector = RedisInstanceMetricsCollector()
collector_registry = CollectorRegistry()
collector_registry.register(metrics_collector)
