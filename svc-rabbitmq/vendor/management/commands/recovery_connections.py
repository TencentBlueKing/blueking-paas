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
from datetime import datetime, timedelta
from operator import itemgetter

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from paas_service.models import ServiceInstance
from vendor.client import Client
from vendor.helper import InstanceHelper
from vendor.models import Cluster

if typing.TYPE_CHECKING:
    from django.core.management.base import ArgumentParser

logger = logging.getLogger(__name__)


def output(msg):
    print(msg)
    logger.info(msg)


class Command(BaseCommand):
    def add_arguments(self, parser: 'ArgumentParser'):
        parser.add_argument("-c", "--cluster", required=True, type=int, help="instance cluster id")
        parser.add_argument("-i", "--instances", nargs="+", help="instance id")
        parser.add_argument("-V", "--vhost", nargs="+", help="virtual host name")
        parser.add_argument("-m", "--max-idle", type=int, required=True, help="max idle seconds")
        parser.add_argument("-r", "--reason", default="idle timeout", help="reason to close connection")
        parser.add_argument("-H", "--peer-host", nargs="+", default=[], help="peer host connected to this cluster")
        parser.add_argument("-s", "--sleep", type=int, default=10, help="sleep seconds before starting next action")
        parser.add_argument(
            "--ignore-heartbeat", action="store_true", default=False, help="ignore connection heartbeat status"
        )
        parser.add_argument(
            "--ignore-consumer",
            action="store_true",
            default=False,
            help="close idle connection even if it still consuming some queue",
        )
        parser.add_argument("--dry-run", action="store_true", default=False, help="dry run")

    def get_vhost_set(self, instances, vhost, *args, **kwargs):
        virtual_hosts = set()
        if vhost:
            virtual_hosts.update(vhost)

        if not instances:
            return virtual_hosts

        for i in ServiceInstance.objects.filter(pk__in=instances):
            helper = InstanceHelper(i)
            credentials = helper.get_credentials()
            virtual_hosts.add(credentials.vhost)

        return virtual_hosts

    def get_client_by_cluster(self, cluster, *args, **kwargs):
        cluster = Cluster.objects.get(pk=cluster)
        return Client.from_cluster(cluster)

    def connection_match_filters(self, virtual_host_set, peer_host_set, connection):
        if virtual_host_set and connection["vhost"] not in virtual_host_set:
            return False

        if peer_host_set and connection["peer_host"] not in peer_host_set:
            return False

        return True

    def convert_connected_at(self, connection):
        return datetime.fromtimestamp(connection["connected_at"] / 1000)

    def is_new_connection(self, now, max_duration, ignore_heartbeat, connection):
        timeout = connection["timeout"]
        if timeout > 0 and not ignore_heartbeat:
            return True

        connected_at = self.convert_connected_at(connection)
        if connected_at + max_duration > now:
            return True

        return False

    def connection_is_idle(self, client, max_duration, now, connection, ignore_consumer):
        if "recv_oct_details" in connection and connection["recv_oct_details"]["rate"] > 0:
            return False

        if "send_oct_details" in connection and connection["send_oct_details"]["rate"] > 0:
            return False
        try:
            return self.connection_channels_are_idle(client, max_duration, now, connection, ignore_consumer)
        except Exception as err:
            output(f"checking connection {connection['name']} channels failed, skip: {err}")
            return False

    def channel_is_activated(self, channel, ignore_consumer):
        if not ignore_consumer and channel["consumer_count"] > 0:
            return True

        if channel["acks_uncommitted"] > 0:
            return True

        if channel["messages_unacknowledged"] > 0:
            return True

        if channel["messages_uncommitted"] > 0:
            return True

        if channel["messages_unconfirmed"] > 0:
            return True

        message_stats = channel.get("message_stats")
        if not message_stats:
            return False

        if "confirm_details" in message_stats and message_stats["confirm_details"]["rate"] > 0:
            return True

        if "publish_details" in message_stats and message_stats["publish_details"]["rate"] > 0:
            return True

        return False

    def connection_channels_are_idle(self, client, max_duration, now, connection, ignore_consumer):
        for ch in client.connection.channels(connection["name"]):
            if self.channel_is_activated(ch, ignore_consumer):
                return False

            idle_since = ch.get("idle_since")
            if not idle_since:
                return False

            if parse_datetime(idle_since) + max_duration > now:
                return False

        return True

    def handle(self, max_idle, dry_run, peer_host, sleep, reason, ignore_heartbeat, ignore_consumer, *args, **kwargs):
        client = self.get_client_by_cluster(*args, **kwargs)
        virtual_hosts = self.get_vhost_set(*args, **kwargs)
        peer_host_set = set(peer_host)
        max_duration = timedelta(seconds=max_idle)

        now = datetime.utcnow()
        connections = []
        for c in client.connection.list():
            if not self.connection_match_filters(virtual_hosts, peer_host_set, c):
                continue

            if self.is_new_connection(now, max_duration, ignore_heartbeat, c):
                continue

            if not self.connection_is_idle(client, max_duration, now, c, ignore_consumer):
                continue

            connections.append(c)

        connections.sort(key=itemgetter("connected_at"))
        output(f"going to close {len(connections)} connections(max duration: {max_duration})")
        for c in connections:
            connected_at = self.convert_connected_at(c)
            output(f"closing connection {c['name']} of vhost {c['vhost']} which connected at {connected_at}")
            if not dry_run:
                try:
                    client.connection.close(c["name"], reason)
                except Exception as err:
                    output(f"close connection {c['name']} of vhost {c['vhost']} failed: {err}")
                else:
                    time.sleep(sleep)
