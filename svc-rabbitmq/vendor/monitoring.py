# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from prometheus_client.core import GaugeMetricFamily
from vendor.client import Client


class ClusterMinimalMetricsCollector:
    """收集集群最核心的指标"""

    def __init__(self, cluster):
        self.cluster = cluster
        self.client = Client.from_cluster(cluster)
        self.cluster_id = str(cluster.pk)

    def collect_overview_object_totals(self, overview):
        family = GaugeMetricFamily(
            "rabbitmq_object_totals",
            "rabbitmq overview objects",
            labels=["cluster", "type"],
        )
        for k, v in overview['object_totals'].items():
            family.add_metric([self.cluster_id, k], v)
        yield family

    def collect_overview_queue_totals(self, overview):
        family = GaugeMetricFamily(
            "rabbitmq_queue_message_totals",
            "number of messages in queue",
            labels=["cluster", "type"],
        )
        queue_totals = overview['queue_totals']
        for k in ["messages", "messages_ready", "messages_unacknowledged"]:
            if k in queue_totals:
                family.add_metric([self.cluster_id, k], queue_totals[k])
        yield family

    def collect_overview_message_stats(self, overview):
        family = GaugeMetricFamily(
            "rabbitmq_message_stats_rate",
            "message stats rate recently",
            labels=["cluster", "type"],
        )

        message_stats = overview["message_stats"]
        for k in [
            "ack",
            "confirm",
            "deliver",
            "deliver_get",
            "deliver_no_ack",
            "disk_reads",
            "disk_writes",
            "drop_unroutable",
            "get",
            "get_empty",
            "get_no_ack",
            "publish",
            "redeliver",
            "return_unroutable",
        ]:
            details = message_stats.get(f"{k}_details") or {}
            if "rate" in details:
                family.add_metric([self.cluster_id, k], details["rate"])

        yield family

    def collect_overview(self):
        overview = self.client.overview()

        yield from self.collect_overview_object_totals(overview)
        yield from self.collect_overview_queue_totals(overview)
        yield from self.collect_overview_message_stats(overview)

    def collect_node_mem(self, nodes):
        mem_used = GaugeMetricFamily(
            "rabbitmq_node_mem_used",
            "total amount of memory used",
            labels=["cluster", "node"],
        )
        mem_limit = GaugeMetricFamily(
            "rabbitmq_node_mem_limit",
            "memory usage high watermark",
            labels=["cluster", "node"],
        )
        mem_alarm = GaugeMetricFamily(
            "rabbitmq_node_mem_alarm",
            "is a memory alarm in effect",
            labels=["cluster", "node"],
        )

        for node in nodes:
            name = node["name"]
            mem_used.add_metric([self.cluster_id, name], node["mem_used"])
            mem_limit.add_metric([self.cluster_id, name], node["mem_limit"])
            mem_alarm.add_metric([self.cluster_id, name], 1 if node["mem_alarm"] else 0)

        yield mem_used
        yield mem_limit
        yield mem_alarm

    def collect_node_disk(self, nodes):
        disk_limit = GaugeMetricFamily(
            "rabbitmq_node_disk_limit",
            "free disk space low watermark",
            labels=["cluster", "node"],
        )
        disk_alarm = GaugeMetricFamily(
            "rabbitmq_node_disk_alarm",
            "is a disk alarm in effect",
            labels=["cluster", "node"],
        )

        for node in nodes:
            name = node["name"]
            disk_limit.add_metric([self.cluster_id, name], node["mem_limit"])
            disk_alarm.add_metric([self.cluster_id, name], 1 if node["mem_alarm"] else 0)

        yield disk_limit
        yield disk_alarm

    def collect_node_fd(self, nodes):
        fd_totals = GaugeMetricFamily(
            "rabbitmq_node_fd_totals",
            "file descriptors available",
            labels=["cluster", "node"],
        )
        fd_used = GaugeMetricFamily(
            "rabbitmq_node_fd_used",
            "file descriptors used",
            labels=["cluster", "node"],
        )
        fd_attempts = GaugeMetricFamily(
            "rabbitmq_node_fd_attempts",
            "file descriptor open attempts",
            labels=["cluster", "node"],
        )
        for node in nodes:
            name = node["name"]
            fd_totals.add_metric([self.cluster_id, name], node["fd_total"])
            fd_used.add_metric([self.cluster_id, name], node["fd_used"])
            fd_attempts.add_metric([self.cluster_id, name], node["io_file_handle_open_attempt_count"])

        yield fd_totals
        yield fd_used
        yield fd_attempts

    def collect_node_socket(self, nodes):
        socket_totals = GaugeMetricFamily(
            "rabbitmq_node_socket_totals",
            "sockets available",
            labels=["cluster", "node"],
        )
        socket_used = GaugeMetricFamily(
            "rabbitmq_node_socket_used",
            "sockets used",
            labels=["cluster", "node"],
        )
        for node in nodes:
            name = node["name"]
            socket_totals.add_metric([self.cluster_id, name], node["sockets_total"])
            socket_used.add_metric([self.cluster_id, name], node["sockets_used"])

        yield socket_totals
        yield socket_used

    def collect_node_proc(self, nodes):
        gc_totals = GaugeMetricFamily(
            "rabbitmq_node_gc_totals",
            "GC runs",
            labels=["cluster", "node"],
        )
        gc_reclaimed = GaugeMetricFamily(
            "rabbitmq_node_gc_reclaimed",
            "bytes reclaimed by GC",
            labels=["cluster", "node"],
        )
        proc_totals = GaugeMetricFamily(
            "rabbitmq_node_proc_total",
            "Erlang process limit",
            labels=["cluster", "node"],
        )
        proc_used = GaugeMetricFamily(
            "rabbitmq_node_proc_used",
            "Erlang processes used",
            labels=["cluster", "node"],
        )
        for node in nodes:
            name = node["name"]
            gc_totals.add_metric([self.cluster_id, name], node["gc_num"])
            gc_reclaimed.add_metric([self.cluster_id, name], node["gc_bytes_reclaimed"])
            proc_totals.add_metric([self.cluster_id, name], node["proc_total"])
            proc_used.add_metric([self.cluster_id, name], node["proc_used"])

        yield gc_totals
        yield gc_reclaimed
        yield proc_totals
        yield proc_used

    def collect_node_basic(self, nodes):
        uptime = GaugeMetricFamily(
            "rabbitmq_node_uptime",
            "uptime",
            labels=["cluster", "node"],
        )
        status = GaugeMetricFamily(
            "rabbitmq_node_status",
            "node is running",
            labels=["cluster", "node"],
        )

        for node in nodes:
            name = node["name"]
            uptime.add_metric([self.cluster_id, name], node["uptime"])
            status.add_metric([self.cluster_id, name], 1 if node["running"] else 0)

        yield uptime
        yield status

    def collect_nodes(self):
        nodes = self.client.nodes()

        yield from self.collect_node_basic(nodes)
        yield from self.collect_node_mem(nodes)
        yield from self.collect_node_disk(nodes)
        yield from self.collect_node_fd(nodes)
        yield from self.collect_node_socket(nodes)
        yield from self.collect_node_proc(nodes)

    def collect(self):
        # https://www.rabbitmq.com/monitoring.html#cluster-wide-metrics
        yield from self.collect_overview()
        # https://www.rabbitmq.com/monitoring.html#node-metrics
        yield from self.collect_nodes()
