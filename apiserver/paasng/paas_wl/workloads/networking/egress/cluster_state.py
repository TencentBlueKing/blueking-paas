# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import copy
import hashlib
import logging
from typing import Dict, List

from django.utils.encoding import force_bytes
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.resources.base.kres import KNode
from paas_wl.infras.resources.utils.basic import EnhancedApiClient

from .models import RegionClusterState

logger = logging.getLogger(__name__)


def generate_state(cluster_name: str, client, ignore_labels: Dict[str, str]) -> RegionClusterState:
    """Generate region state for a single region"""

    nodes = get_nodes(client)
    nodes = list(filter_nodes_with_labels(nodes, ignore_labels))
    nodes_name = sorted([node.metadata.name for node in nodes])
    nodes_digest = get_digest_of_nodes_name(nodes_name)

    # Use a shorter version of the digest as name, cstate -> "Cluster State"
    next_version = RegionClusterState.objects.filter(cluster_name=cluster_name).count() + 1
    name = "eng-cstate-{}-{}".format(nodes_digest[:8], next_version)

    try:
        state = RegionClusterState.objects.get(cluster_name=cluster_name, nodes_digest=nodes_digest)
        logger.info("legacy state found in database, current cluster state has already been recorded")
    except RegionClusterState.DoesNotExist:
        pass
    else:
        return state

    cluster = Cluster.objects.get(name=cluster_name)
    return RegionClusterState.objects.create(
        cluster_name=cluster_name,
        name=name,
        nodes_digest=nodes_digest,
        nodes_cnt=len(nodes),
        nodes_name=list(nodes_name),
        nodes_data=[compact_node_data(node.to_dict()) for node in nodes],
        tenant_id=cluster.tenant_id,
    )


def filter_nodes_with_labels(nodes: List[ResourceInstance], ignore_labels: Dict[str, str]):
    for node in nodes:
        # If node contains any label in ignore_labels, ignore this node
        labels = node.metadata.get("labels", {})
        should_ignore = any(True for k, v in ignore_labels.items() if labels.get(k) == v)
        if not should_ignore:
            yield node


def get_digest_of_nodes_name(nodes_name: List[str]) -> str:
    """Get the digest of current node name list"""
    return hashlib.sha1(force_bytes(",".join(nodes_name))).hexdigest()


def compact_node_data(node_data: dict):
    """Compact node data by removing some big but not necessary fields"""
    result = copy.deepcopy(node_data)
    result["status"].pop("images", None)
    result["status"].pop("conditions", None)
    return result


def format_nodes_data(nodes: List[dict]) -> List[dict]:
    """Format node data dict into smaller dict with {name, internal_ip_address} keys

    :param nodes: Node data returned by kubernetes apiserver
    """
    results = []
    for node in nodes:
        try:
            addresses = node["status"]["addresses"]
        except KeyError:
            pass

        # Get the first item in list whose type == InternalIP
        ip = next((addr["address"] for addr in (addresses or []) if addr.get("type") == "InternalIP"), "")
        results.append({"name": node["metadata"]["name"], "internal_ip_address": ip})
    return results


# TODO: Update these two functions to accept `Cluster` argument


def get_nodes(client: EnhancedApiClient) -> List[ResourceInstance]:
    """Return a list a all kubernetes nodes in current cluster"""
    return KNode(client).ops_batch.list({}).items


def sync_state_to_nodes(client: EnhancedApiClient, state):
    """Sync a RegionClusterState object to current cluster, which means:

    - Update the labels of all nodes
    - Engine apps may use the labels to customize their schedule strategy
    """
    labels = state.to_labels()
    for node_name in state.nodes_name:
        node = KNode(client).get(node_name)
        node.metadata.labels = {**node.metadata.get("labels", {}), **labels}
        logger.debug(f"Patching node object {node_name} with labels {labels}")
        KNode(client).ops_name.replace_or_patch(node_name, node, update_method="patch")
