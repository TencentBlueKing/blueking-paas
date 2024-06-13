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
import arrow
from django.core.management.base import BaseCommand
from django.utils import timezone

from paas_wl.infras.resources.base.base import get_all_cluster_names, get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KPod


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", dest="dry_run", help="dry run", action="store_true")
        parser.add_argument(
            "--timeout", help="slug pod timeout(default is 3600s), please use seconds", type=int, default=60 * 60
        )

    def handle(self, dry_run, timeout, *args, **options):
        now = timezone.now()

        for cluster_name in get_all_cluster_names():
            client = get_client_by_cluster_name(cluster_name)
            pods = KPod(client).ops_batch.list(labels={"category": "slug-builder"})
            timeout_count = 0
            # normally, there is only one slug instance
            for pod in pods.items:
                timedelta = now - arrow.get(pod.metadata.creationTimestamp).datetime
                if timedelta.total_seconds() > timeout:
                    # do delete operation
                    print(f"{pod.metadata.name} had started more than one hour, going to delete it")
                    timeout_count += 1

                    if dry_run:
                        print("DRY-RUN: cleaned !")
                        continue
                    # there is no delete method available in scheduler client
                    # use k8s API directly
                    KPod(client).delete(name=pod.metadata.name, namespace=pod.metadata.namespace)
                    print("cleaned !")

            print(f"{cluster_name} has {timeout_count} timeout pods, cleaned\n")
