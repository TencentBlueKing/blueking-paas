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
from django.conf import settings
from vendor.client import Client
from vendor.command import FederationBaseCommand
from vendor.exceptions import ResourceNotFound
from vendor.models import Cluster


class VhostNotAliveError(Exception):
    pass


class VhostNotFound(Exception):
    pass


class Command(FederationBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-q", "--queue-pattern", default=".*", help="queue pattern")
        parser.add_argument("-p", "--priority", default=10, type=int, help="policy priority")
        parser.add_argument(
            "--ignore-idle-vhost",
            default=False,
            action="store_true",
            help="ignore virtual host without connection",
        )

        super().add_arguments(parser)

    def test_vhost(self, client: Client, vhost: str):
        try:
            if not client.alive(vhost):
                raise VhostNotAliveError(vhost)
        except ResourceNotFound:
            raise VhostNotFound(vhost)

    def set_upstream(
        self,
        cluster: Cluster,
        upstream: Cluster,
        name,
        vhost,
        queue_pattern,
        priority,
        ignore_idle_vhost,
    ):
        cluster_client = Client.from_cluster(cluster)
        self.test_vhost(cluster_client, vhost)

        upstream_client = Client.from_cluster(upstream)
        self.test_vhost(upstream_client, vhost)

        if ignore_idle_vhost and not upstream_client.connection.list():
            print(f"vhost {vhost} is idle, skipped")
            return

        # 临时用户
        username = self.get_username(cluster, upstream, name, vhost)
        password = self.get_password(cluster, upstream, name, vhost)
        upstream_client.user.create(username, password, settings.RABBITMQ_DEFAULT_USER_TAGS)
        upstream_client.user.set_permission(username, vhost)

        # 设置上游
        cluster_client.federation.set_upstream(
            name,
            f"amqp://{username}:{password}@{upstream.host}:{upstream.port}",
            vhost,
        )

        # 联邦策略
        cluster_client.user_policy.create(
            vhost,
            name,
            {
                "pattern": queue_pattern,
                "priority": priority,
                "apply-to": "queues",
                "definition": {
                    "federation-upstream": name,
                },
            },
        )

    def handle(
        self,
        upstream_cluster,
        vhost,
        exclude_vhost,
        queue_pattern,
        name,
        on_error_resume,
        priority,
        ignore_idle_vhost,
        *args,
        **kwargs,
    ):
        cluster = self.get_cluster(*args, **kwargs)
        upstream = self.get_cluster(cluster=upstream_cluster)

        vhosts = self.get_available_vhosts(cluster, upstream, vhost, exclude_vhost)

        for i in vhosts:
            print(f"handling vhost: {i}")
            try:
                self.set_upstream(
                    cluster=cluster,
                    upstream=upstream,
                    name=name,
                    vhost=i,
                    queue_pattern=queue_pattern,
                    priority=priority,
                    ignore_idle_vhost=ignore_idle_vhost,
                )
            except Exception as err:
                if not on_error_resume:
                    raise

                print(err)
