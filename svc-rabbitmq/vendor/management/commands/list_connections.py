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
from vendor.command import ClusterBaseCommand


class Command(ClusterBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--exclude-peer-host", nargs="+", default=[], help="cluster id")

        super().add_arguments(parser)

    def handle(self, exclude_peer_host, *args, **kwargs):
        client = self.get_client_by_cluster(*args, **kwargs)
        exclude_peer_hosts = set(exclude_peer_host)

        connections = []
        for c in client.connection.list():
            peer_host = c.get("peer_host")
            if not peer_host or peer_host in exclude_peer_hosts:
                continue

            parts = [c["vhost"], c["name"], c["user"], peer_host, c["node"], c["connected_at"]]
            connections.append(tuple(map(str, parts)))

        connections.sort()
        for i in connections:
            print("\t".join(i))
