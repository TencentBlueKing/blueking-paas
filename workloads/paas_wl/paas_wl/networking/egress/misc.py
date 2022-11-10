"""Egress(cluster outgoing traffic) related module"""
from typing import Dict

from paas_wl.cluster.models import Cluster
from paas_wl.resources.utils.app import get_scheduler_client

from .models import format_nodes_data, get_digest_of_nodes_name


def get_cluster_egress_ips(cluster: Cluster) -> Dict:
    """Return cluster's egress IP addresses. by default, cluster's node IPs will be returned"""
    sched_client = get_scheduler_client(cluster_name=cluster.name)
    nodes = sched_client.get_nodes()
    nodes_name = sorted([node.metadata.name for node in nodes])

    nodes_data = [node.to_dict() for node in sched_client.get_nodes()]
    nodes_digest = get_digest_of_nodes_name(nodes_name)
    egress_ips = [n['internal_ip_address'] for n in format_nodes_data(nodes_data)]
    return {'digest_version': nodes_digest, 'egress_ips': egress_ips}
