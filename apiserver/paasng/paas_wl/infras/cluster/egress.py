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

"""Cluster egress information for infrastructure consumers."""

import hashlib
from typing import TypedDict

from django.utils.encoding import force_bytes

from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KNode


class ClusterEgressIps(TypedDict):
    digest_version: str
    egress_ips: list[str]


def get_cluster_egress_info(cluster_name: str) -> ClusterEgressIps:
    """Return the egress IP addresses and node-set digest for a cluster."""
    cluster = Cluster.objects.get(name=cluster_name)
    client = get_client_by_cluster_name(cluster.name)
    nodes = KNode(client).ops_batch.list({}).items
    node_names = sorted(node.metadata.name for node in nodes)
    egress_ips = [_get_internal_ip(node.to_dict()) for node in nodes]
    return ClusterEgressIps(
        digest_version=hashlib.sha1(force_bytes(",".join(node_names))).hexdigest(),  # noqa: S324
        egress_ips=egress_ips,
    )


def _get_internal_ip(node: dict) -> str:
    """Extract a Kubernetes node's internal IP address."""
    addresses = node.get("status", {}).get("addresses", [])
    return next((address["address"] for address in addresses if address.get("type") == "InternalIP"), "")
