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
from datetime import timedelta

from vendor.client import Client
from vendor.command import InstancesBasedCommand
from vendor.definitions import Channel, Connection

if typing.TYPE_CHECKING:
    from django.core.management.base import CommandParser

logger = logging.getLogger(__name__)


class Command(InstancesBasedCommand):
    help = "Evict connection in federation cluster"

    def add_arguments(self, parser: 'CommandParser'):
        super().add_arguments(parser)

        parser.add_argument("-t", "--timeout", type=int, default=1800, help="migrate timeout")
        parser.add_argument("-I", "--interval", type=int, default=10, help="check interval")
        parser.add_argument(
            "-f",
            "--force",
            default=False,
            action="store_true",
            help="force close all connection before finished",
        )
        parser.add_argument("-m", "--max-idle-seconds", type=int, required=True, default=60, help="max idle seconds")
        parser.add_argument("-r", "--reason", default="connection eviction", help="connection close message")
        parser.add_argument("-p", "--safe-peer-host", nargs="+", help="safe peer host")
        parser.add_argument("-P", "--peer-host", nargs="+", help="peer host")
        parser.add_argument("--dry-run", default=False, action="store_true", help="dry run mode")

    def has_consumer_channel(self, channels: typing.List[Channel]):
        for ch in channels:
            if ch.is_consumer():
                return True
        return False

    def consumer_channels_idle(self, channels: typing.List[Channel], max_idle: timedelta):
        idle = True

        for i in channels:
            if i.is_consumer() and not i.is_idle(ignore_consumer=True, max_idle=max_idle):
                idle = False

        return idle

    def handle_consumer(self, connections: typing.List[Connection], client: Client, *args, **kwargs):
        for connection in connections:
            if connection.is_busy():
                continue

    def close_connection(self, client: Client, connection: Connection, dry_run: bool, reason: str, *args, **kwargs):
        print(f"going to close connection {connection}")
        if dry_run:
            return True

        try:
            client.connection.close(connection.name, reason)
            return True
        except Exception as err:
            print(f"close connection {connection} failed: {err}")
            return False

    def run_once(
        self,
        client: Client,
        max_idle_seconds: int,
        safe_peer_host: typing.List[str],
        peer_host: typing.List[str],
        *args,
        **kwargs,
    ):
        vhost_set = self.get_vhost_set(*args, **kwargs)
        if vhost_set:
            print(f"evicting connections in vhosts: {', '.join(vhost_set)}")

        safe_peer_host_set = set()
        if safe_peer_host:
            safe_peer_host_set.update(safe_peer_host)
            print(f"safe peer hosts: {', '.join(safe_peer_host_set)}")

        peer_host_set = set()
        if peer_host:
            peer_host_set.update(peer_host)
            print(f"evicting connections for peer hosts: {', '.join(peer_host_set)}")

        rest_connections: typing.List[Connection] = []

        for i in client.connection.list():
            connection = Connection(**i)
            if vhost_set and connection.vhost not in vhost_set:
                continue

            if peer_host_set and connection.peer_host not in peer_host_set:
                continue

            if safe_peer_host_set and connection.peer_host in safe_peer_host_set:
                continue

            try:
                chs = client.connection.channels(connection.name)
            except Exception as err:
                print(f"list channels for connection {connection} failed: {err}, check in next time")
                rest_connections.append(connection)
                continue

            channels = [Channel(**i) for i in chs]

            if not self.has_consumer_channel(channels):
                print(f"connection {connection} is for publisher")
            elif not self.consumer_channels_idle(channels, timedelta(seconds=max_idle_seconds)):
                print(f"connection {connection} is activating, skipped")
                rest_connections.append(connection)
                continue
            else:
                print(f"idle connection {connection} is for consumer")

            if not self.close_connection(client, connection, *args, **kwargs):
                rest_connections.append(connection)

        return rest_connections

    def run(self, force: bool, interval: int, timeout: int, *args, **kwargs):
        client = self.get_client_by_cluster(*args, **kwargs)
        rest_connections = []

        start_at = time.time()
        while start_at + timeout > time.time():
            time.sleep(interval)
            print("checking connections")

            try:
                rest_connections = self.run_once(client, *args, **kwargs)
            except Exception as err:
                print(f"handle error: {err}, retring")
                continue

            if not rest_connections:
                print("all connections are closed")
                return

            print(f"got {len(rest_connections)} connections, going to sleep")

        if force:
            print("force closing all connections")
            for c in rest_connections:
                self.close_connection(client, c, *args, **kwargs)

    def handle(self, *args, **kwargs):
        try:
            self.run(*args, **kwargs)
        except KeyboardInterrupt:
            print("exit")
