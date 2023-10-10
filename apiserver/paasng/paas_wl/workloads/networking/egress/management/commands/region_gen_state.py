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
"""Generate a new state of all regions

Examples:

    python manage.py region_gen_state --region your-region --cluster-name=your-cluster-name
"""
import logging
import sys

from django.core.management.base import BaseCommand

from paas_wl.infras.cluster.models import Cluster
from paas_wl.workloads.networking.egress.misc import sync_state_to_nodes
from paas_wl.workloads.networking.egress.models import generate_state
from paas_wl.infras.resources.utils.basic import get_client_by_cluster_name

logger = logging.getLogger("commands")


class Command(BaseCommand):
    """This command stores current cluster status in database with all nodes data. it should be
    executed after any updates on cluster nodes.

    The stored RegionClusterState objects is useful for things like "scheduling by cluster generation".

    By forcing app to be scheduled to only some fixed nodes of the cluster, app developer don't
    need to re-configure the IP whitelist of their external services when new nodes were added
    into the existed cluster.
    """

    help = 'Generates region state based on current cluster status'

    def add_arguments(self, parser):
        parser.add_argument(
            "--region",
            default="",
            type=str,
            help="specify a region name, by default this command will process all regions " "defined in settings",
        )
        parser.add_argument(
            "--cluster-name",
            default="",
            type=str,
            help="specify a cluster name, by default this command will process all clusters",
        )
        parser.add_argument(
            "--no-input",
            default=False,
            action='store_true',
            help='Skip prompt',
        )
        parser.add_argument(
            "--ignore-labels",
            default=[],
            type=str,
            nargs='+',
            help=(
                "ignore nodes if it matches any of these labels, "
                "will always include 'node-role.kubernetes.io/master=true'"
            ),
        )
        parser.add_argument(
            "--include-masters", default=False, type=bool, help="Include master nodes or not, default to no"
        )

    def handle(self, *args, **options):
        all_regions = set(Cluster.objects.values_list("region", flat=True))
        if options["region"]:
            if options["region"] not in all_regions:
                print(f'{options["region"]} is not a valid region name')
                sys.exit(1)

            regions = [options["region"]]
        else:
            regions = list(all_regions)

        ignore_labels = options["ignore_labels"]
        ignore_labels = [value.split("=") for value in ignore_labels]
        if any(len(label) != 2 for label in ignore_labels):
            raise ValueError("Invalid label given!")

        if not options["include_masters"]:
            ignore_labels.append(('node-role.kubernetes.io/master', 'true'))

        cluster_name = options.get('cluster_name')

        for region in regions:
            logger.debug(f"Make scheduler client from region: {region}")
            for cluster in Cluster.objects.filter(region=region):
                if cluster_name and cluster.name != cluster_name:
                    continue

                logger.info(f"Will generate state for [{region}/{cluster.name}]...")
                if not options.get('no_input') and input("Confirm? (y/n, default: n) ").lower() != 'y':
                    continue

                try:
                    client = get_client_by_cluster_name(cluster_name=cluster.name)

                    logger.info(f"Generating state for [{region} - {cluster.name}]...")
                    state = generate_state(region, cluster.name, client, ignore_labels=ignore_labels)

                    logger.info("Syncing the state to nodes...")
                    sync_state_to_nodes(client, state)
                except Exception:
                    logger.exception("Unable to generate state")
                    continue
