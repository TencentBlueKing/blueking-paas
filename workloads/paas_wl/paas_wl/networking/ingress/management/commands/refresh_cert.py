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
"""A tool to refresh shared TLS certs. Cert files are used to support HTTPS
protocol for applications. When a cert file was updated during a renewal, this
command has to be called in order to refresh all Secret resources which contains
the content of certificate.
"""
import sys
from typing import Sequence

import cryptography.x509
from django.core.management.base import BaseCommand

from paas_wl.cluster.models import Cluster
from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.certs.utils import pick_shared_cert, update_or_create_secret_by_cert
from paas_wl.networking.ingress.models import AppDomain, AppDomainSharedCert, AppSubpath
from paas_wl.platform.applications.models.app import EngineApp


class Command(BaseCommand):
    """This command refreshes all ingress resources related with given shared certificate"""

    help = "Refresh certificate's related Secret resources"

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str, required=True, help="Name of certification object")
        parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode")

    def handle(self, *args, **options) -> None:
        return self.handle_refresh(options)

    def handle_refresh(self, options):
        """Handle refresh action"""
        name = options['name']
        try:
            cert = AppDomainSharedCert.objects.get(name=name)
        except AppDomainSharedCert.DoesNotExist:
            self.exit_with_error(f'Cert "{name}" does not exist')

        # Find out all affected EngineApps
        d_apps = self.find_subdomain_apps(cert)
        p_apps = self.find_subpath_apps(cert)
        # Sort the app list to get a deterministic result
        apps = sorted(set(d_apps) | set(p_apps), key=lambda app: app.name)
        self.print(f'Found affected apps(sub-domain/sub-path): {len(d_apps)}/{len(p_apps)}')
        self.print(f'Deduplicated overall count: {len(apps)}')

        # Ask user to double-check the certificate content
        self.display_cert(cert)
        if input("Do you want to proceed?(yes/no) ").lower() not in {'y', 'yes'}:
            self.exit_with_error("quit")

        # The update will walk through all affected applications. Each cert only
        # have a single copy of Secret in one namespace although it may be shared
        # by multiple Ingresses, so this approach will doing fine.
        self.update_secrets(apps, cert, options['dry_run'])
        return

    def find_subdomain_apps(self, cert: AppDomainSharedCert) -> Sequence[EngineApp]:
        """Find all affected EngineApps for subdomain addresses"""
        self.print("Refreshing Secret resources for sub-domains...")
        app_ids = AppDomain.objects.filter(shared_cert=cert).values_list('app_id').distinct()
        return list(EngineApp.objects.filter(pk__in=app_ids))

    def find_subpath_apps(self, cert: AppDomainSharedCert):
        """Find all affected EngineApps for subpath addresses"""
        self.print("Refreshing Secret resources for sub-paths...")
        # Find related applications, first filter all clusters which configured
        # "sub_path_domains" and it's host matches given certificate.
        cluster_names = []
        for cluster in Cluster.objects.all():
            for domain in cluster.ingress_config.sub_path_domains:
                if pick_shared_cert(cluster.region, domain.name) == cert:
                    cluster_names.append(cluster.name)
                    break

        if not cluster_names:
            return []

        app_ids = AppSubpath.objects.filter(region=cert.region).values_list('app_id').distinct()
        apps = []
        # Although AppSubpath has "cluster_name" field, it's value is not set at
        # this moment. So it's impossible to filter affected applications by simply
        # querying "cluster_name" field.
        #
        # TODO: Improve below logic when AppSubpath model was improved
        for app in EngineApp.objects.filter(pk__in=app_ids).order_by('name'):
            if get_cluster_by_app(app).name in cluster_names:
                apps.append(app)
        return apps

    def update_secrets(self, apps: Sequence[EngineApp], cert: AppDomainSharedCert, dry_run: bool):
        """Update Secret resource which was created by given certificate and
        lives in each EngineApp's namespace.
        """
        cnt = len(apps)
        error_cnt = 0
        self.print(f"App(Namespace) count: {cnt}")
        for i, app in enumerate(apps, start=1):
            self.print(f"({i}/{cnt}) Processing {app}..")
            if dry_run:
                self.print('(dry-run mode) Update skipped.')
                continue

            try:
                update_or_create_secret_by_cert(app, cert)
            except Exception as e:
                self.print(f'Unable to update Secret for {app}: {str(e).splitlines()[0]}')
                error_cnt += 1
        self.print(f'Update Secrets finished, error count: {error_cnt}')

    def display_cert(self, cert: AppDomainSharedCert):
        """Display the information of given cert object"""
        try:
            cert_obj = cryptography.x509.load_pem_x509_certificate(bytes(cert.cert_data, 'utf-8'))
        except ValueError as e:
            self.exit_with_error(f"{cert.name}'s certification file is not valid: {e}")
            return

        self.print(f"Name of Issuer: {cert_obj.issuer}")
        self.print(f"Name of Subject: {cert_obj.subject}")
        self.print(f"Not valid after: {cert_obj.not_valid_after}")

    def exit_with_error(self, message: str, code: int = 2):
        """Exit execution and print error message"""
        self.print(f'Error: {message}')
        sys.exit(2)

    @staticmethod
    def print(message: str) -> None:
        """A simple wrapper for print function, can be replaced with other implementations"""
        print(message)
