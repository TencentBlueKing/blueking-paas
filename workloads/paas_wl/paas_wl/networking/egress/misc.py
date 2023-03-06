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
"""Egress(cluster outgoing traffic) related module"""
from typing import List, TypedDict

from paas_wl.cluster.models import Cluster
from paas_wl.networking.egress.models import format_nodes_data, get_digest_of_nodes_name
from paas_wl.resources.utils.app import get_scheduler_client


class ClusterEgressIps(TypedDict):
    digest_version: str
    egress_ips: List[str]


def get_cluster_egress_ips(cluster: Cluster) -> ClusterEgressIps:
    """Return cluster's egress IP addresses. by default, cluster's node IPs will be returned"""
    sched_client = get_scheduler_client(cluster_name=cluster.name)
    nodes = sched_client.get_nodes()
    nodes_name = sorted([node.metadata.name for node in nodes])

    nodes_data = [node.to_dict() for node in sched_client.get_nodes()]
    nodes_digest = get_digest_of_nodes_name(nodes_name)
    egress_ips = [n['internal_ip_address'] for n in format_nodes_data(nodes_data)]
    return ClusterEgressIps(digest_version=nodes_digest, egress_ips=egress_ips)
