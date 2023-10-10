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
"""Analyze all app's deploy status, highlight problematic stats
"""
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from django.core.management.base import BaseCommand
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.infras.cluster.models import Cluster
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KNode, KPod

logger = logging.getLogger("commands")


class Command(BaseCommand):
    """Analyze all applications's deployment, highlight problematic stats, includes:

    - (same-host) "prod" process's pods have been assigned to one single same host
    - (multiple-clusters) A single process was deployed on multiple clusters
    - (node-state-mismatch) Node's state labels does not match records in database
    """

    help = 'show problematic deploy stats'

    def add_arguments(self, parser):
        parser.add_argument(
            "--cluster-name",
            default="",
            type=str,
            help="specify a cluster name, by default this command will scan all clusters",
        )

    def handle(self, *args, **options):
        cluster_name = options.get('cluster_name')
        clusters = Cluster.objects.all()
        if cluster_name:
            clusters = clusters.filter(name=cluster_name)

        process_stats = build_process_stats(clusters)
        # Report stats to console
        report_same_host(process_stats)
        report_mul_clusters(process_stats)

        records = list(NodeStateMismatch(clusters).get_results())
        report_node_state_mismatch(records)


BatchProcessStats = Dict['AppProcess', 'ProcessStat']


def build_process_stats(clusters: Iterable[Cluster]) -> BatchProcessStats:
    """Build total statistics data of given clusters"""
    process_stats: BatchProcessStats = {}
    for cluster in clusters:
        logger.debug("Generating stats for cluster: %s", cluster)
        try:
            client = get_client_by_cluster_name(cluster_name=cluster.name)
        except ValueError:
            logger.warning(f'Unable to make client for {cluster.name}')
            continue

        pods = KPod(client).ops_label.list(labels={})
        for pod in pods.items:
            try:
                proc = AppProcess.from_pod(pod)
            except ValueError:
                continue
            if proc not in process_stats:
                process_stats[proc] = ProcessStat()

            # Update stats objects
            stat = process_stats[proc]
            cluster_stat = stat.get_stat(cluster.name)
            hostIP = pod.status.hostIP
            cluster_stat.assigned_hosts.append(hostIP)
    return process_stats


def report_same_host(process_stats: BatchProcessStats):
    """Find and report all "prod" processes whose instances were assigned to one single host"""
    results = []
    for proc, stat in process_stats.items():
        if proc.env != 'prod':
            continue

        for cstat in stat.cluster_stats:
            if cstat.has_single_host():
                results.append((proc, cstat))

    # Print stats to console
    print()
    print('> SAME HOST')
    print('> ("prod" process\'s pods have been assigned to one single same host)')
    print()
    cols_tmpl = '{0:<20}{1:<8}{2:<18}{3:<18}{4:<14}{5}'
    print(cols_tmpl.format('App Code', 'Env', 'Process', 'Cluster', 'Num of Pods', 'Hosts'))
    for proc, cstat in results:
        hosts = ','.join(cstat.assigned_hosts)
        num_of_pods = len(cstat.assigned_hosts)
        print(cols_tmpl.format(proc.app_code, proc.env, proc.process_id, cstat.cluster_name, num_of_pods, hosts))


def report_mul_clusters(process_stats: BatchProcessStats):
    """Find and report all processes which were deployed to multiple clusters"""
    results = []
    for proc, stat in process_stats.items():
        if len(stat.cluster_stats) > 1:
            cluster_names = ','.join(cstat.cluster_name for cstat in stat.cluster_stats)
            results.append((proc, cluster_names))

    # Print stats to console
    print()
    print('> MULTIPLE CLUSTERS')
    print('> (A single process was deployed on multiple clusters)')
    print()
    cols_tmpl = '{0:<20}{1:<8}{2:<18}{3:<18}'
    print(cols_tmpl.format('App Code', 'Env', 'Process', 'Clusters'))
    for proc, cluster_names in results:
        print(cols_tmpl.format(proc.app_code, proc.env, proc.process_id, cluster_names))


@dataclass
class NodeMismatchRecord:
    cluster_name: str
    node_name: str
    desired_labels: List[str]
    current_labels: List[str]


class NodeStateMismatch:
    """Find nodes with wrong state related labels"""

    def __init__(self, clusters: Iterable[Cluster]):
        self.clusters = clusters

    def get_results(self) -> Iterable[NodeMismatchRecord]:
        """Return records which contain node_name and details of mismatched labels"""
        desired_groups = self._get_desired_labels()
        current_groups = self._get_current_labels()
        for cluster_name, nodes_data in current_groups.items():
            desired_labels_nodes = desired_groups.get(cluster_name, {})

            for node_name, current_labels in nodes_data.items():
                # Compare labels, if mismatch, yield result
                desired_labels = desired_labels_nodes.get(node_name, set())
                if current_labels != desired_labels:
                    yield NodeMismatchRecord(
                        cluster_name=cluster_name,
                        node_name=node_name,
                        desired_labels=desired_labels,
                        current_labels=current_labels,
                    )

    def _get_desired_labels(self) -> Dict:
        """Get nodes' desired state labels from database records, results were grouped by cluster_name"""
        results: Dict[str, Dict] = defaultdict(dict)
        for state in RegionClusterState.objects.all().order_by('created'):
            c_data = results[state.cluster_name]
            for node_name in state.nodes_name:
                c_data.setdefault(node_name, set()).add(state.name)
        return results

    def _get_current_labels(self) -> Dict:
        """Get nodes's current state labels by querying apiserver"""
        results: Dict[str, Dict] = defaultdict(dict)
        # Get all region stated related names, used for filtering labels later
        all_state_names = set(RegionClusterState.objects.all().values_list('name', flat=True))
        for cluster in self.clusters:
            c_data = results[cluster.name]
            client = get_client_by_cluster_name(cluster_name=cluster.name)
            nodes = KNode(client).ops_label.list(labels={})
            for node in nodes.items:
                # Find all region state related labels
                node_name = node.metadata.name
                c_data[node_name] = set(dict(node.metadata.labels)) & all_state_names
        return results


def report_node_state_mismatch(records: Iterable[NodeMismatchRecord]):
    """Report nodes with wrong state labels"""
    # Print stats to console
    print()
    print('> NODE STATE MISMATCH')
    print('> (Node\'s state labels does not match records in database)')
    print()
    cols_tmpl = '{0:<20}{1:<32}{2:<40}{3:<40}'
    print(cols_tmpl.format('Cluster', 'Node', 'Labels(desired)', 'Labels(current)'))
    for record in records:
        print(
            cols_tmpl.format(
                record.cluster_name,
                record.node_name,
                ', '.join(record.desired_labels),
                ', '.join(record.current_labels),
            )
        )


# Helper dataclasses


@dataclass(frozen=True)
class AppProcess:
    """App's process object"""

    app_code: str
    region: str
    env: str
    process_id: str

    @classmethod
    def from_pod(cls, pod: ResourceInstance):
        """Create an AppProcess object from pod manifest

        :raises ValueError: when given manifest was not managed by engine app
        """
        labels = pod.metadata.get('labels', {})
        app_code = labels.get('app_code')
        if not app_code:
            raise ValueError("Pod isn't a valid app resource, no 'app_code' can be found in metadata.labels")

        return cls(
            app_code=app_code,
            region=labels.get('region', ''),
            env=labels.get('env', ''),
            process_id=labels.get('process_id', ''),
        )


@dataclass
class ProcessClusterStat:
    """Process stats in one cluster"""

    cluster_name: str
    assigned_hosts: List[str]

    def has_single_host(self) -> bool:
        """Check if there is only one same assigned_host"""
        return len(set(self.assigned_hosts)) == 1


@dataclass
class ProcessStat:
    """Process stats"""

    cluster_stats: List[ProcessClusterStat] = field(default_factory=list)

    def get_stat(self, cluster_name: str) -> ProcessClusterStat:
        """Get cluster stat object, create one if not exists"""
        for cstat in self.cluster_stats:
            if cluster_name == cstat.cluster_name:
                return cstat

        # Create a new stat object and append it to current container
        new_cstat = ProcessClusterStat(cluster_name=cluster_name, assigned_hosts=[])
        self.cluster_stats.append(new_cstat)
        return new_cstat
