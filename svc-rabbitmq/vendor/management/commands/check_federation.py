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
from collections import defaultdict
from typing import Any, Dict

from vendor.client import Client
from vendor.command import FederationBaseCommand
from vendor.models import Cluster


class Command(FederationBaseCommand):
    _upstream_connections: Dict[str, Any]
    _cluster_connections: Dict[str, Any]

    def _get_connections(self, client: "Client"):
        connections = defaultdict(list)
        for i in client.connection.list():
            if "Federation link" in i.get("user_provided_name", ""):
                continue

            connections[i.get("vhost")].append(i)

        return connections

    def get_upstream_connections(self, client: "Client", vhost: "str"):
        if not hasattr(self, "_upstream_connections"):
            self._upstream_connections = self._get_connections(client)

        return self._upstream_connections.get(vhost)

    def get_cluster_connections(self, client: "Client", vhost: "str"):
        if not hasattr(self, "_cluster_connections"):
            self._cluster_connections = self._get_connections(client)

        return self._cluster_connections.get(vhost)

    def check_federation_upstream_status(
        self,
        client: Client,
        vhost,
    ):
        for status in client.federation.list_status(vhost):
            if status.get("status") != "running":
                return False

        return True

    def check_vhost(
        self,
        cluster: Cluster,
        upstream: Cluster,
        vhost,
    ):
        cluster_client = Client.from_cluster(cluster)
        upstream_client = Client.from_cluster(upstream)

        has_upstream = bool(cluster_client.federation.list_upstream(vhost))
        has_upstream_connections = bool(self.get_upstream_connections(upstream_client, vhost))
        has_cluster_connections = bool(self.get_cluster_connections(cluster_client, vhost))
        is_status_ok = self.check_federation_upstream_status(cluster_client, vhost)

        # 有连接的 vhost 必须是联邦
        if has_upstream is has_upstream_connections:
            return

        if not has_upstream:
            print(f"vhost {vhost} is not a federation")
        elif has_upstream_connections:
            print(f"vhost {vhost} is not a federation but connections exists")
        elif not has_cluster_connections:
            print(f"vhost {vhost} has no upstream connections")
        elif not is_status_ok:
            print(f"vhost {vhost} federation is not ok")

    def handle(
        self,
        upstream_cluster,
        vhost,
        exclude_vhost,
        on_error_resume,
        *args,
        **kwargs,
    ):
        cluster = self.get_cluster(*args, **kwargs)
        upstream = self.get_cluster(cluster=upstream_cluster)

        vhosts = self.get_available_vhosts(cluster, upstream, vhost, exclude_vhost)

        for i in vhosts:
            print(f"handling vhost: {i}")
            try:
                self.check_vhost(
                    cluster=cluster,
                    upstream=upstream,
                    vhost=i,
                )
            except Exception as err:
                if not on_error_resume:
                    raise

                print(err)
