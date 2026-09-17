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

        yield from self._build_families(statuses)

        instances_family, success_family = self._build_self_families()
        instances_family.add_metric([], len(statuses))
        success_family.add_metric([], int(success))
        yield instances_family
        yield success_family

    def describe(self):
        """prometheus_client 注册时会调用, 返回空指标以避免触发真实采集"""
        yield from self._build_families([])
        yield from self._build_self_families()

    @staticmethod
    def _build_families(statuses: list[RedisInstanceStatus]) -> list[GaugeMetricFamily]:
        labels = RedisInstance.as_label_keys()
        alive = GaugeMetricFamily("redis_instance_alive", "whether the redis instance is available", labels=labels)
        memory_usage = GaugeMetricFamily(
            "redis_instance_memory_usage_rate", "memory usage rate of the redis instance", labels=labels
        )
        connection_usage = GaugeMetricFamily(
            "redis_instance_connection_usage_rate", "connection usage rate of the redis instance", labels=labels
        )
        oom_killed = GaugeMetricFamily(
            "redis_instance_oom_killed", "whether the redis container was oom killed", labels=labels
        )
        exporter_up = GaugeMetricFamily(
            "redis_instance_exporter_up",
            "whether the redis exporter metrics were collected; absent when the instance has no exporter",
            labels=labels,
        )

        for status in statuses:
            label_values = status.instance.as_label_values()
            # 取不到的值不产出样本(显式缺失), 不用 0 冒充; gauge 值统一转 float(bool 即 1/0)
            for family, value in (
                (alive, status.alive),
                (memory_usage, status.memory_usage_rate),
                (connection_usage, status.connection_usage_rate),
                (oom_killed, status.oom_killed),
                (exporter_up, status.exporter_up),
            ):
                if value is not None:
                    family.add_metric(label_values, value)

        return [alive, memory_usage, connection_usage, oom_killed, exporter_up]

    @staticmethod
    def _build_self_families() -> list[GaugeMetricFamily]:
        """采集链路的自监控: 本次采集覆盖了多少实例 / 是否成功"""
        instances_family = GaugeMetricFamily("redis_instance_collect_instances", "number of instances collected")
        success_family = GaugeMetricFamily(
            "redis_instance_collect_success", "whether this collection finished without unexpected error"
        )

        return [instances_family, success_family]


metrics_collector = RedisInstanceMetricsCollector()
collector_registry = CollectorRegistry()
collector_registry.register(metrics_collector)
