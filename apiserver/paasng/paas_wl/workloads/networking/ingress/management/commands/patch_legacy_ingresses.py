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
"""Patch existed Kubernetes service object, make it compatible with new services/manager interface
"""
import logging
from fnmatch import fnmatch

import arrow
from django.core.management.base import BaseCommand

from paas_wl.workloads.networking.ingress.managers import LegacyAppIngressMgr
from paas_wl.workloads.networking.ingress.utils import make_service_name
from paas_wl.bk_app.applications.models import Release, WlApp

logger = logging.getLogger('commands')


class Command(BaseCommand):
    """This command patchs legacy app ingresses:

    Update annotation field:
        - `nginx.ingress.kubernetes.io/configuration-snippet`
        - `nginx.ingress.kubernetes.io/server-snippet`
    """

    help = 'Patch legacy app ingresses'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', help="dry run", action="store_true")
        parser.add_argument('-p', '--pattern', default="", help="domain pattern")
        parser.add_argument('-t', '--process_type', default="web", help="app process type")
        parser.add_argument('--with-create', action="store_true", help="create ingress when not exists")
        parser.add_argument('--app-created-after', default=None, help="filter applications by created field")
        parser.add_argument(
            '-a', '--app', dest="apps", default=None, nargs="+", help="legacy app name which need to patch"
        )

    def handle(self, apps, dry_run, pattern, process_type, with_create, app_created_after, *args, **options):
        qs = WlApp.objects.all().order_by('created')
        if apps:
            qs = qs.filter(name__in=apps)

        # Filter apps by "created" field if given
        if app_created_after:
            app_created_after_dt = arrow.get(app_created_after).datetime
            qs = qs.filter(created__gte=app_created_after_dt)

        for app in qs:
            self._patch_app_ingress(app, dry_run, pattern, process_type, with_create)

    def _patch_app_ingress(self, app: WlApp, dry_run, pattern, process_type, with_create):
        # Only process released apps
        if not Release.objects.filter(app=app, build__isnull=False).exists():
            return False

        logger.info(f"checking ingress for app {app.name} with pattern {pattern}")
        logger.info(f"app was created at {app.created}")

        mgr = LegacyAppIngressMgr(app)
        service_name = None
        can_sync = False
        try:
            domains = mgr.list_desired_domains()
        except Exception:
            logger.exception("list domains failed for app %s", app.name)
            return

        for domain in domains:
            if fnmatch(domain.host, pattern):
                can_sync = not dry_run
                print(f"domain {domain.host} match, ready to sync")
            else:
                print(f"domain {domain.host} mismatch, abort")
                break

        if with_create:
            service_name = make_service_name(app, process_type)
            print(f"will create ingress for process {process_type}: {service_name}")

        if can_sync:
            print(f"syncing ingress for app {app.name}")
            try:
                mgr.sync(service_name)
            except Exception as err:
                logger.error("sync ingresses failed for app %s, err: %s", app.name, err)
