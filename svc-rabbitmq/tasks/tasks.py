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
import logging
import typing
from collections import Counter, defaultdict
from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.core.management import call_command
from paas_service.models import ServiceInstance
from vendor.client import Client
from vendor.exceptions import ResourceNotFound
from vendor.helper import InstanceHelper
from vendor.models import Cluster

from .helper import Task

logger = logging.getLogger(__name__)

inf = float("+inf")


@dataclass
class ClusterResult:
    cluster_id: 'int'

    def as_label_values(self):
        return [str(self.cluster_id)]

    @classmethod
    def as_label_keys(cls):
        return ["bk_cluster"]


@dataclass
class InstanceResult(ClusterResult):
    instance_id: 'UUID'
    vhost: 'str'

    def as_label_values(self):
        labels = super().as_label_values()
        return labels + [str(self.instance_id), self.vhost]

    @classmethod
    def as_label_keys(cls):
        labels = super().as_label_keys()
        return labels + ["bk_instance", "vhost"]


class CronCheckClustersAlive(Task):
    @classmethod
    def apply(cls) -> 'typing.Dict[str, CheckClusterAlive.Result]':
        """check all cluster is alive"""
        logger.info("checking clusters if is alive")
        result = {}
        for cluster in Cluster.objects.filter(enable=True):
            result[cluster.name] = CheckClusterAlive.apply(cluster)
        return result


class CheckClusterAlive(Task):
    @dataclass
    class Result(ClusterResult):
        ok: 'bool'

    @classmethod
    def apply(cls, cluster: 'Cluster', virtual_host: 'str' = "/") -> 'CheckClusterAlive.Result':
        """check cluster is alive in vhost"""
        logger.debug("checking cluster %s if is alive", cluster)
        client = Client.from_cluster(cluster)
        ok = None
        try:
            ok = client.alive(virtual_host)
        except Exception as err:
            logger.exception(err)

        return cls.Result(cluster_id=cluster.pk, ok=ok)


class CheckInstanceAlive(Task):
    @dataclass
    class Result(InstanceResult):
        ok: 'bool'

    @classmethod
    def apply(cls, instance: 'ServiceInstance') -> 'CheckInstanceAlive.Result':
        """check instance vhost if is available"""
        logger.debug("checking rabbitmq instance %s if is alive", instance)
        helper = InstanceHelper(instance)
        cluster = helper.get_cluster()
        credentials = helper.get_credentials()
        result = CheckClusterAlive.apply(cluster, credentials.vhost)
        return cls.Result(instance_id=instance.pk, cluster_id=result.cluster_id, vhost=credentials.vhost, ok=result.ok)


class CheckInstancesCronTask(Task):
    task: 'Task'
    name: 'str'

    @classmethod
    def apply(cls):
        logger.info("checking instances task %s", cls.name)
        tasks = []
        for i in ServiceInstance.objects.filter(to_be_deleted=False):
            tasks.append((i, cls.task.apply_async(i)))

        results = {}
        for i, t in tasks:
            try:
                results[str(i.uuid)] = t.get()
            except Exception:
                logger.exception("check instance %s alive failed", i.uuid)

        return results


class CronCheckInstancesAlive(CheckInstancesCronTask):
    task = CheckInstanceAlive
    name = "alive"


class Healthz(Task):
    @classmethod
    def apply(cls, value):
        return -value


class CheckQueueStatusMixin:
    @dataclass
    class QueueStatus:
        name: 'str'
        max_length: 'float'
        message_ttl: 'float'
        has_dlx_exchange: 'bool'
        messages: 'int'
        messages_ready: 'int'
        messages_unacknowledged: 'int'
        consumers: 'int'
        memory: 'int'
        message_bytes: 'int'
        message_bytes_paged_out: 'int'

    @classmethod
    def get_queue_attribute(cls, name: 'str', policy: 'dict', arguments: 'dict', default):
        if name in policy:
            return policy[name]

        name = f"x-{name}"
        if name in arguments:
            return arguments[name]

        return default

    @classmethod
    def get_queue_status(cls, queue) -> 'CheckQueueStatusMixin.QueueStatus':
        arguments = queue.get("arguments", {})
        policy = queue.get("effective_policy_definition", {})
        defaults = {
            "name": "",
            "memory": 0,
            "message_bytes": 0,
            "message_bytes_paged_out": 0,
            "consumers": 0,
            "messages": 0,
            "messages_ready": 0,
            "messages_unacknowledged": 0,
        }
        stats = {k: queue.get(k, v) for k, v in defaults.items()}
        return cls.QueueStatus(
            max_length=cls.get_queue_attribute("max-length", policy, arguments, inf),
            message_ttl=cls.get_queue_attribute("message-ttl", policy, arguments, inf),
            has_dlx_exchange=bool(cls.get_queue_attribute("x-dead-letter-exchange", policy, arguments, "")),
            **stats,
        )


class CheckInstanceQueueStatus(CheckQueueStatusMixin, Task):
    @dataclass
    class Result(InstanceResult):
        queues: 'typing.List[CheckInstanceQueueStatus.QueueStatus]'

    @classmethod
    def apply(cls, instance: 'ServiceInstance') -> 'CheckInstanceQueueStatus.Result':
        logger.debug("checking rabbitmq instance %s queue status", instance)

        helper = InstanceHelper(instance)
        cluster = helper.get_cluster()
        credentials = helper.get_credentials()
        client = Client.from_cluster(cluster)
        vhost = credentials.vhost
        status = []

        for queue in client.queue.list(vhost):
            try:
                status.append(cls.get_queue_status(queue))
            except Exception:
                logger.exception("collecting queue status %s failed", queue)

        return cls.Result(queues=status, cluster_id=cluster.id, instance_id=instance.pk, vhost=vhost)


class CronCheckInstancesQueueStatus(CheckInstancesCronTask):
    task = CheckInstanceQueueStatus
    name = "queue status"


class CheckInstanceDLXQueueStatus(CheckQueueStatusMixin, Task):
    @dataclass
    class Result(InstanceResult):
        status: 'CheckInstanceDLXQueueStatus.QueueStatus'

    @classmethod
    def apply(
        cls,
        instance: 'ServiceInstance',
        name: 'str' = settings.RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE,
    ) -> 'typing.Optional[CheckInstanceDLXQueueStatus.Result]':
        helper = InstanceHelper(instance)
        cluster = helper.get_cluster()
        credentials = helper.get_credentials()
        client = Client.from_cluster(cluster)
        try:
            queue = client.queue.get(name, credentials.vhost)
        except ResourceNotFound:
            return None
        status = cls.get_queue_status(queue)
        return cls.Result(status=status, cluster_id=cluster.id, instance_id=instance.pk, vhost=credentials.vhost)


class CronCheckInstanceDLXQueueStatus(CheckInstancesCronTask):
    task = CheckInstanceDLXQueueStatus
    name = "qlx queue status"


class CheckClusterConnectionStatus(Task):
    @dataclass
    class ConnectionStatus(ClusterResult):
        vhost: 'str'
        running: 'int'
        idle: 'int'
        blocking: 'int'
        blocked: 'int'
        others: 'int'

    @classmethod
    def apply(cls, cluster: 'Cluster') -> 'typing.List[CronCheckInstanceConnectionStatus.ConnectionStatus]':
        logger.debug("checking rabbitmq connections status for cluster %s", cluster.name)
        connections = defaultdict(Counter)
        client = Client.from_cluster(cluster)
        for connection in client.connection.list():
            state = connection.get("state", "unknown")
            connections[connection["vhost"]].update([state])

        return [
            cls.ConnectionStatus(
                cluster_id=cluster.id,
                vhost=vhost,
                running=status["running"],
                idle=status["idle"],
                blocking=status["blocking"],
                blocked=status["blocked"],
                others=status["unknown"],
            )
            for vhost, status in connections.items()
        ]


class CronCheckInstanceConnectionStatus(Task):
    @dataclass
    class ConnectionStatus(InstanceResult):
        running: 'int'
        idle: 'int'
        blocking: 'int'
        blocked: 'int'
        others: 'int'

    @classmethod
    def apply(cls):
        grouped_instances = defaultdict(dict)
        for i in ServiceInstance.objects.filter(to_be_deleted=False):
            helper = InstanceHelper(i)
            credentials = helper.get_credentials()
            grouped_instances[helper.get_cluster_id()][credentials.vhost] = i

        results = {}
        for cluster_id, instances in grouped_instances.items():
            try:
                status = CheckClusterConnectionStatus.apply(Cluster.objects.get(pk=cluster_id))
            except Exception:
                logger.exception("check connection for cluster %s failed", cluster_id)
                continue

            for s in status:
                instance = instances.get(s.vhost)
                if not instance:
                    continue

                results[str(instance.uuid)] = cls.ConnectionStatus(
                    cluster_id=cluster_id,
                    vhost=s.vhost,
                    instance_id=instance.pk,
                    running=s.running,
                    idle=s.idle,
                    blocked=s.blocked,
                    blocking=s.blocking,
                    others=s.others,
                )

        return results


class CheckInstanceLimits(Task):
    @dataclass
    class Result(InstanceResult):
        connections: 'float'
        queues: 'float'

    @classmethod
    def apply(cls, instance: 'ServiceInstance') -> 'CheckInstanceLimits.Result':
        logger.debug("checking rabbitmq instance %s if is alive", instance)
        helper = InstanceHelper(instance)
        cluster = helper.get_cluster()
        credentials = helper.get_credentials()
        client = Client.from_cluster(cluster)

        for policy in client.limit_policy.get(credentials.vhost):
            if policy["vhost"] == credentials.vhost:
                value = policy["value"]
                return cls.Result(
                    instance_id=instance.pk,
                    cluster_id=cluster.id,
                    vhost=credentials.vhost,
                    connections=value.get("max-connections", inf),
                    queues=value.get("max-queues", inf),
                )


class CronCheckInstanceLimits(CheckInstancesCronTask):
    task = CheckInstanceLimits
    name = "instance limit policies"


class ConnectionRecovery(Task):
    duration = getattr(
        settings, "RABBITMQ_CONNECTION_RECOVERY_MAX_IDLE", settings.RABBITMQ_CONNECTION_RECOVERY_INTERVAL * 60 // 3
    )
    delay = getattr(settings, "RABBITMQ_CONNECTION_RECOVERY_DELAY", 1)

    @classmethod
    def apply(cls):
        for c in Cluster.objects.filter(enable=True):
            call_command(
                "recovery_connections",
                "--cluster",
                c.id,
                "--max-idle",
                cls.duration,
                "--sleep",
                cls.delay,
                "--ignore-consumer",
            )


cluster_alive = CronCheckClustersAlive("clusters_alive", interval=settings.RABBITMQ_CLUSTER_ALIVE_CHECK_INTERVAL)
instance_alive = CronCheckInstancesAlive("instances_alive", interval=settings.RABBITMQ_INSTANCE_ALIVE_CHECK_INTERVAL)
instance_queue = CronCheckInstancesQueueStatus(
    "instances_queue", interval=settings.RABBITMQ_INSTANCE_QUEUE_CHECK_INTERVAL
)
instance_dlx_queue = CronCheckInstanceDLXQueueStatus(
    "instances_dlx_queue", interval=settings.RABBITMQ_INSTANCE_QUEUE_CHECK_INTERVAL
)
connection_status = CronCheckInstanceConnectionStatus(
    "connection_status", interval=settings.RABBITMQ_INSTANCE_VHOST_CHECK_INTERVAL
)
instance_limits = CronCheckInstanceLimits("instance_limits", interval=settings.RABBITMQ_INSTANCE_VHOST_CHECK_INTERVAL)
connection_recovery = ConnectionRecovery(
    "connection_recovery", interval=settings.RABBITMQ_CONNECTION_RECOVERY_INTERVAL
)


def ready():
    cluster_alive.register_cron_task()
    instance_alive.register_cron_task()
    instance_queue.register_cron_task()
    instance_dlx_queue.register_cron_task()
    connection_status.register_cron_task()
    instance_limits.register_cron_task()
    connection_recovery.register_cron_task()
