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
import copy
import hashlib
import logging
from typing import Dict, List

from django.conf import settings
from django.db import models
from django.utils.encoding import force_bytes
from jsonfield import JSONField

from paas_wl.workloads.networking.constants import NetworkProtocol
from paas_wl.bk_app.applications.models import AuditedModel, WlApp
from paas_wl.infras.resources.utils.basic import label_toleration_providers

logger = logging.getLogger(__name__)


class RegionClusterState(AuditedModel):
    """A RegionClusterState is a state which describes what the cluster is in a specified moment. it
    may includes:

    - How many nodes do the cluster have?
    - What are their names?
    - What are their IP addresses?
    """

    region = models.CharField(max_length=32)
    cluster_name = models.CharField(max_length=32, null=True)
    name = models.CharField('informative name of state', max_length=64)
    nodes_digest = models.CharField(max_length=64, db_index=True)
    nodes_cnt = models.IntegerField(default=0)
    nodes_name = JSONField(default=[], blank=True)
    nodes_data = JSONField(default=[], blank=True)

    def to_labels(self) -> Dict:
        """To kubernetes lables. The labels will be patched into all kubernetes nodes and also
        exists in app's node_selector if the app was bind with current state.
        """
        return {self.name: "1"}

    class Meta:
        unique_together = ("region", "cluster_name", "name")
        get_latest_by = 'created'
        ordering = ['-created']


class RCStateAppBinding(AuditedModel):
    """If an app was bind with one RegionClusterState instance, it means that the app will not be
    scheduled onto any nodes other than those were defined in that RegionClusterState instance.
    """

    app = models.OneToOneField(WlApp, on_delete=models.CASCADE)
    state = models.ForeignKey(RegionClusterState, null=True, on_delete=models.CASCADE)


def filter_nodes_with_labels(nodes, ignore_labels):
    for node in nodes:
        # If node contains any label in ignore_labels, ignore this node
        labels = node.metadata.get('labels', {})
        should_ignore = any(True for k, v in ignore_labels if labels.get(k) == v)
        if not should_ignore:
            yield node


# TODO: Move there functions out of models module to avoid circular imports
def generate_state(region: str, cluster_name: str, client, ignore_labels: List) -> RegionClusterState:
    """Generate region state for a single region"""
    from paas_wl.workloads.networking.egress.misc import get_nodes

    nodes = get_nodes(client)
    nodes = list(filter_nodes_with_labels(nodes, ignore_labels))
    nodes_name = sorted([node.metadata.name for node in nodes])
    nodes_digest = get_digest_of_nodes_name(nodes_name)

    # Use a shorter version of the digest as name, cstate -> "Cluster State"
    next_version = RegionClusterState.objects.filter(region=region, cluster_name=cluster_name).count() + 1
    name = "eng-cstate-{}-{}".format(nodes_digest[:8], next_version)

    try:
        state = RegionClusterState.objects.get(region=region, cluster_name=cluster_name, nodes_digest=nodes_digest)
        logger.info("legacy state found in database, current cluster state has already been recorded")
        return state
    except RegionClusterState.DoesNotExist:
        pass

    return RegionClusterState.objects.create(
        region=region,
        cluster_name=cluster_name,
        name=name,
        nodes_digest=nodes_digest,
        nodes_cnt=len(nodes),
        nodes_name=list(nodes_name),
        nodes_data=[compact_node_data(node.to_dict()) for node in nodes],
    )


def compact_node_data(node_data: dict):
    """Compact node data by removing some big but not necessary fields"""
    result = copy.deepcopy(node_data)
    result["status"].pop("images", None)
    result["status"].pop("conditions", None)
    return result


def get_digest_of_nodes_name(nodes_name: List[str]) -> str:
    """Get the digest of current node name list"""
    return hashlib.sha1(force_bytes(",".join(nodes_name))).hexdigest()


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


class EgressSpec(AuditedModel):
    wl_app = models.OneToOneField(WlApp, on_delete=models.CASCADE, db_constraint=False)
    replicas = models.IntegerField(default=1)
    cpu_limit = models.CharField(max_length=16)
    memory_limit = models.CharField(max_length=16)

    def build_manifest(self):
        return {
            "apiVersion": "bkbcs.tencent.com/v1alpha1",
            "kind": "Egress",
            "metadata": {
                "name": self.wl_app.name,
                "namespace": self.wl_app.namespace,
            },
            "spec": {
                "replicas": self.replicas,
                "gateImage": settings.BCS_EGRESS_GATE_IMAGE,
                "podIPImage": settings.BCS_EGRESS_POD_IP_IMAGE,
                "podDefaultDisabled": False,
                "gateArgs": ["-backend=ipvs", "-outer=eth0"],
                "annotations": {
                    "tke.cloud.tencent.com/vpc-ip-claim-delete-policy": "Never",
                    "tke.cloud.tencent.com/networks": "tke-route-eni",
                },
                "podCidrs": settings.BCS_EGRESS_POD_CIDRS,
                "resources": {
                    "cpu": self.cpu_limit,
                    "memory": self.memory_limit,
                    "tke.cloud.tencent.com/eni-ip": "1",
                },
                "rules": [
                    {
                        "dport": r.dst_port,
                        "host": r.host,
                        "protocol": r.protocol,
                        "sport": r.src_port,
                        "service": r.service,
                    }
                    for r in self.rules.all()
                ],
            },
        }


class EgressRule(AuditedModel):
    """BCS Egress.spec.rules"""

    spec = models.ForeignKey(EgressSpec, on_delete=models.CASCADE, related_name='rules')
    # host 是目标服务的域名/IP，dport 为目标服务的端口
    # egress pod 会对目标是 host:dport 的流量做转发
    dst_port = models.IntegerField('目标端口')
    host = models.CharField('目标主机', max_length=128)
    # protocol 协议，一般是 TCP，也可以是 UDP
    protocol = models.CharField('协议', choices=NetworkProtocol.get_django_choices(), max_length=32)
    # service 指定后，会在同名命名空间中创建名称为该值的 service，sport 为 service 的端口
    # 在启用定制版的 coredns 后，服务可以通过访问 service 达到原有的按域名访问的效果
    # 一般来说，service 与 host 值相同，dport 与 sport 值相同
    src_port = models.IntegerField('源端口')
    service = models.CharField('服务名', max_length=128)


@label_toleration_providers.register_labels
def _get_labels_for_binding(app: WlApp) -> Dict[str, str]:
    """Inject ClusterState labels when bound"""
    try:
        binding = RCStateAppBinding.objects.get(app=app)
    except RCStateAppBinding.DoesNotExist:
        pass
    else:
        return binding.state.to_labels()
    return {}
