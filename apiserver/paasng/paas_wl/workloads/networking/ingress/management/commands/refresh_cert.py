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

"""A tool to refresh shared TLS certs. Cert files are used to support HTTPS
protocol for applications. When a cert file was updated during a renewal, this
command has to be called in order to refresh all Secret resources which contains
the content of certificate.
"""

import sys
from functools import partial
from typing import Iterable, List, Sequence

import cryptography.x509
from django.core.management.base import BaseCommand

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.workloads.networking.ingress.certs import pick_shared_cert, update_or_create_secret_by_cert
from paas_wl.workloads.networking.ingress.models import AppDomain, AppDomainSharedCert, AppSubpath


class Command(BaseCommand):
    """This command refreshes all ingress resources related with given shared certificate"""

    help = "Refresh certificate's related Secret resources"

    def add_arguments(self, parser):
        parser.add_argument("--tenant_id", type=str, required=True, help="The tenant ID")
        parser.add_argument("--name", type=str, required=True, help="Name of certification object")
        parser.add_argument(
            "--full-scan",
            action="store_true",
            help=(
                "Before refreshing, scan all domains in the given tenant completely first, update the "
                '"shared_cert" field of the domain object if a match is found, helpful when the cert is newly added.'
            ),
        )
        parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode")

    def handle(self, *args, **options) -> None:
        return self.handle_refresh(options)

    def handle_refresh(self, options):
        """Handle refresh action"""
        tenant_id = options["tenant_id"]
        name = options["name"]
        try:
            cert = AppDomainSharedCert.objects.get(tenant_id=tenant_id, name=name)
        except AppDomainSharedCert.DoesNotExist:
            self.exit_with_error(f'Cert "{name}" does not exist in tenant "{tenant_id}"')

        # If full scan is enabled, scan all domains and update the cert field if needed
        if options["full_scan"]:
            self.scan_and_update(cert, options["dry_run"])

        # Find out all affected WlApps
        d_apps = self.find_subdomain_apps(cert)
        p_apps = self.find_subpath_apps(cert)
        # Sort the app list to get a deterministic result
        apps = sorted(set(d_apps) | set(p_apps), key=lambda app: app.name)
        self.print(f"Found affected apps(sub-domain/sub-path): {len(d_apps)}/{len(p_apps)}")
        self.print(f"Deduplicated overall count: {len(apps)}")

        # Ask user to double-check the certificate content
        self.display_cert(cert)
        if input("Do you want to proceed?(yes/no) ").lower() not in {"y", "yes"}:
            self.exit_with_error("quit")

        # The update will walk through all affected applications. Each cert only
        # have a single copy of Secret in one namespace, although it may be shared
        # by multiple Ingresses, so this approach will do fine.
        self.update_secrets(apps, cert, options["dry_run"])

    def scan_and_update(self, cert: AppDomainSharedCert, dry_run: bool):
        """Scan all domains in the cert's tenant, update the cert related fields if needed."""
        # Make a print function which print message with current context
        _print = partial(self.print, title="update_cert_fields")

        _print("Scanning all domains to find those whose host matches the given cert...")
        matches: List[AppDomain] = list(find_uninitialized_domains(cert))
        if not matches:
            _print(self.style.SUCCESS("No domains found."))
            return

        _print(f"Found {len(matches)} domains.")
        if input("Do you want to update the cert fields of these domains?(yes/no) ").lower() not in {"y", "yes"}:
            _print("Update canceled.")
            return

        # Update the "shared_cert" field
        if not dry_run:
            for domain in matches:
                domain.shared_cert = cert
                domain.save(update_fields=["shared_cert", "updated"])
            _print(self.style.SUCCESS(f"{len(matches)} domain objects updated."))
        else:
            _print("(dry-run mode) Update skipped.")

    def find_subdomain_apps(self, cert: AppDomainSharedCert) -> Sequence[WlApp]:
        """Find all affected WlApps for subdomain addresses"""
        self.print("Refreshing Secret resources for sub-domains...")
        app_ids = AppDomain.objects.filter(shared_cert=cert).values_list("app_id").distinct()
        return list(WlApp.objects.filter(pk__in=app_ids))

    def find_subpath_apps(self, cert: AppDomainSharedCert):
        """Find all affected WlApps for subpath addresses"""
        self.print("Refreshing Secret resources for sub-paths...")
        # Find related applications, first filter all clusters which configured
        # "sub_path_domains" and it's host matches given certificate.
        cluster_names = []
        for cluster in Cluster.objects.all():
            for domain in cluster.ingress_config.sub_path_domains:
                # TODO: Tenant_id
                if pick_shared_cert(cluster.tenant_id, domain.name) == cert:
                    cluster_names.append(cluster.name)
                    break

        if not cluster_names:
            return []

        app_ids = AppSubpath.objects.filter(tenant_id=cert.tenant_id).values_list("app_id").distinct()
        apps = []
        # Although AppSubpath has "cluster_name" field, it's value is not set at
        # this moment. So it's impossible to filter affected applications by simply
        # querying "cluster_name" field.
        #
        # TODO: Improve below logic when AppSubpath model was improved
        for app in WlApp.objects.filter(pk__in=app_ids).order_by("name"):
            if get_cluster_by_app(app).name in cluster_names:
                apps.append(app)
        return apps

    def update_secrets(self, apps: Sequence[WlApp], cert: AppDomainSharedCert, dry_run: bool):
        """Update Secret resource which was created by given certificate and lives in each WlApp's namespace."""
        cnt = len(apps)
        error_cnt = 0
        self.print(f"App(Namespace) count: {cnt}")
        for i, app in enumerate(apps, start=1):
            self.print(f"({i}/{cnt}) Processing {app}..")
            if dry_run:
                self.print("(dry-run mode) Update skipped.")
                continue

            try:
                update_or_create_secret_by_cert(app, cert)
            except Exception as e:
                self.print(f"Unable to update Secret for {app}: {str(e).splitlines()[0]}")
                error_cnt += 1
        self.print(self.style.SUCCESS(f"Update Secrets finished, error count: {error_cnt}"))

    def display_cert(self, cert: AppDomainSharedCert):
        """Display the information of given cert object"""
        try:
            cert_obj = cryptography.x509.load_pem_x509_certificate(bytes(cert.cert_data, "utf-8"))
        except ValueError as e:
            self.exit_with_error(f"{cert.name}'s certification file is not valid: {e}")
            return

        self.print(f"Name of Issuer: {cert_obj.issuer}")
        self.print(f"Name of Subject: {cert_obj.subject}")
        self.print(f"Not valid after: {cert_obj.not_valid_after}")

    def exit_with_error(self, message: str, code: int = 2):
        """Exit execution and print error message"""
        self.print(self.style.NOTICE(f"Error: {message}"))
        sys.exit(2)

    def print(self, message: str, title: str = "refresh") -> None:
        """A simple wrapper for print function, can be replaced with other implementations

        :param message: The message to be printed
        :param title: Use this title to distinguish different print messages
        """
        if title:
            print(self.style.SUCCESS(f"[{title.upper()}] ") + message)
        else:
            print(message)


def find_uninitialized_domains(cert: AppDomainSharedCert) -> Iterable[AppDomain]:
    """Find all domains which matches the given certificate but not initialized yet"""
    for domain in AppDomain.objects.filter(tenant_id=cert.tenant_id).iterator():
        if domain.cert or domain.shared_cert:
            continue
        if cert.match_hostname(domain.host):
            yield domain
