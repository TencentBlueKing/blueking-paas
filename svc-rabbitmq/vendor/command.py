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
import hashlib
import logging
from typing import TYPE_CHECKING, Iterable, Set, cast

from django.core.management.base import BaseCommand
from paas_service.models import ServiceInstance
from vendor.client import Client
from vendor.helper import InstanceHelper
from vendor.models import Cluster

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

logger = logging.getLogger(__name__)


class ClusterBaseCommand(BaseCommand):
    def add_arguments(self, parser: 'CommandParser'):
        parser.add_argument("-c", "--cluster", required=True, type=int, help="cluster id")

        super().add_arguments(parser)

    def get_cluster(self, cluster, *args, **kwargs) -> Cluster:
        return Cluster.objects.get(pk=cluster)

    def get_client_by_cluster(self, *args, **kwargs):
        return Client.from_cluster(self.get_cluster(*args, **kwargs))


class InstancesBasedCommand(ClusterBaseCommand):
    def add_arguments(self, parser: 'CommandParser'):
        parser.add_argument("-i", "--instances", nargs="+", help="instance id")
        parser.add_argument("-V", "--vhost", nargs="+", default=[], help="virtual host name")

        super().add_arguments(parser)

    def get_vhost_set(self, instances, vhost, cluster=None, *args, **kwargs):
        virtual_hosts = set()
        if vhost:
            virtual_hosts.update(vhost)

        if not instances:
            return virtual_hosts

        for i in self.get_instances(instances, cluster):
            helper = InstanceHelper(i)
            credentials = helper.get_credentials()
            virtual_hosts.add(credentials.vhost)

        return virtual_hosts

    def get_instances(self, instances, cluster=None, *args, **kwargs):
        instances = []

        for i in ServiceInstance.objects.filter(pk__in=instances):
            helper = InstanceHelper(i)
            if cluster and helper.get_cluster_id() != cluster:
                continue

            instances.append(i)

        return instances


class FederationBaseCommand(ClusterBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-u", "--upstream-cluster", required=True, help="upstream cluster id")
        parser.add_argument("-n", "--name", default="federation", help="federation name")
        parser.add_argument("-V", "--vhost", nargs="+", default=[], help="virtual host name")
        parser.add_argument("-E", "--exclude-vhost", nargs="+", default=["/"], help="excluded virtual host name")
        parser.add_argument("--on-error-resume", default=False, action="store_true", help="on error resume")

        super().add_arguments(parser)

    def get_available_vhosts(
        self, cluster: Cluster, upstream: Cluster, specified: Iterable[str], excluded: Iterable[str]
    ):
        cluster_client = Client.from_cluster(cluster)
        upstream_client = Client.from_cluster(upstream)

        cluster_vhosts = cast(Set[str], {i["name"] for i in cluster_client.virtual_host.list()})
        upstream_vhosts = cast(Set[str], {i["name"] for i in upstream_client.virtual_host.list()})

        vhosts = upstream_vhosts & cluster_vhosts
        vhosts = vhosts | set(specified)
        vhosts = vhosts - set(excluded)
        return vhosts

    def get_username(self, cluster: Cluster, upstream: Cluster, name: str, vhost: str):
        hexdigest = hashlib.sha1(f"{cluster.pk}:{cluster.name}-{vhost}".encode("utf-8")).hexdigest()
        return f"{name}-{hexdigest[:12]}"

    def get_password(self, cluster: Cluster, upstream: Cluster, name: str, vhost: str):
        return hashlib.sha1(
            f"{cluster.pk}:{cluster.name}-{upstream.pk}:{upstream.name}-{name}-{vhost}".encode("utf-8"),
        ).hexdigest()
