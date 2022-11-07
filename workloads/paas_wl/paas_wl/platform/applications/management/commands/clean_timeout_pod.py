# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from kubernetes import client as client_mod

from paas_wl.resources.base.base import get_all_cluster_names
from paas_wl.resources.utils.app import get_scheduler_client


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', dest="dry_run", help="dry run", action="store_true")
        parser.add_argument(
            '--timeout', help="slug pod timeout(default is 3600s), please use seconds", type=int, default=60 * 60
        )

    def handle(self, dry_run, timeout, *args, **options):
        now = timezone.now()

        for cluster_name in get_all_cluster_names():
            scheduler_client = get_scheduler_client(cluster_name=cluster_name)
            pods = client_mod.CoreV1Api(scheduler_client.client).list_pod_for_all_namespaces(
                label_selector='category=slug-builder'
            )

            timeout_count = 0
            # normally, there is only one slug instance
            for pod in pods.items:
                timedelta = now - pod.status.start_time
                if timedelta.total_seconds() > timeout:
                    # do delete operation
                    print(f"{pod.metadata.name} had started more than one hour, going to delete it")
                    timeout_count += 1

                    if dry_run:
                        print("DRY-RUN: cleaned !")
                        continue
                    # there is no delete method available in scheduler client
                    # use k8s API directly
                    client_mod.CoreV1Api(scheduler_client.client).delete_namespaced_pod(
                        name=pod.metadata.name, namespace=pod.metadata.namespace, body=client_mod.V1DeleteOptions()
                    )
                    print("cleaned !")

            print(f"{cluster_name} has {timeout_count} timeout pods, cleaned\n")
