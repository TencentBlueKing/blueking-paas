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
import logging
from typing import List, Set

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.workloads.networking.ingress.certs import pick_shared_cert, update_or_create_secret_by_cert
from paas_wl.workloads.networking.ingress.constants import AppSubpathSource
from paas_wl.workloads.networking.ingress.entities import PIngressDomain
from paas_wl.workloads.networking.ingress.models import AppSubpath

from .base import AppIngressMgr

logger = logging.getLogger(__name__)


def assign_subpaths(app: WlApp, subpaths: List[str], default_service_name: str):
    """Assign subpaths to app, may update multiple apps's Ingress resources
    if a path's ownership has been changed from one app to another.

    :param subpaths: List of subpaths
    :param default_service_name: if ingress resource does not exist yet, use this service_name
        as default.
    """
    affected_apps = save_subpaths(app, subpaths)
    for app in affected_apps:
        logger.info("Syncing app %s's subpaths ingress...", app.name)
        SubPathAppIngressMgr(app).sync(default_service_name=default_service_name, delete_when_empty=True)


def save_subpaths(app: WlApp, subpaths: List[str]) -> Set[WlApp]:
    """Save subpaths to database, return apps affected by this save operation.

    :param subpaths: List of subpaths
    """
    existed_subpaths = AppSubpath.objects.filter(
        region=app.region, subpath__in=subpaths, source=AppSubpathSource.DEFAULT
    )
    affected_apps = {obj.app for obj in existed_subpaths}

    for subpath in subpaths:
        AppSubpath.objects.update_or_create(
            region=app.region, subpath=subpath, defaults={"app": app, "source": AppSubpathSource.DEFAULT}
        )
    # Remove subpaths which are no longer bound with app
    AppSubpath.objects.filter(app=app, source=AppSubpathSource.DEFAULT).exclude(subpath__in=subpaths).delete()

    affected_apps.add(app)
    return affected_apps


class SubPathAppIngressMgr(AppIngressMgr):
    """manage ingress which providing access via subpath

    - Every app has a ingress resource in its own namespace
    - These ingress resources has same host and different sub-paths
    - Ingress controller will merge those ingress resources into a big "server" block

    More details: https://kubernetes.github.io/ingress-nginx/how-it-works/#building-the-nginx-model
    """

    def make_ingress_name(self) -> str:
        return f"{self.app.region}-{self.app.scheduler_safe_name}--subpath"

    def list_desired_domains(self) -> List[PIngressDomain]:
        """List all desired domains for current app"""
        cluster = get_cluster_by_app(self.app)
        domains = cluster.ingress_config.sub_path_domains
        if not domains:
            logger.info("sub-path domain was not configured for cluster, return empty result")
            return []

        path_objs = AppSubpath.objects.filter(app=self.app).order_by("created")
        paths = [obj.subpath for obj in path_objs]
        if not paths:
            return []

        return [self.create_ingress_domain(domain.name, paths, domain.https_enabled) for domain in domains]

    def create_ingress_domain(self, host: str, path_prefix_list: List[str], https_enabled: bool) -> PIngressDomain:
        """Create a domain object, will create HTTPS related Secret resource on demand"""
        if not https_enabled:
            return PIngressDomain(host=host, path_prefix_list=path_prefix_list, tls_enabled=False)

        cert = pick_shared_cert(self.app.region, host)
        if cert:
            secret_name, created = update_or_create_secret_by_cert(self.app, cert)
            if created:
                logger.info("created a secret %s for host %s", secret_name, host)

            return PIngressDomain(
                host=host,
                path_prefix_list=path_prefix_list,
                tls_enabled=https_enabled,
                tls_secret_name=secret_name,
            )
        else:
            # Disable HTTPS and write a warning message
            logger.warning("no valid cert can be found for domain: %s, disable HTTPS.", host)
            return PIngressDomain(host=host, path_prefix_list=path_prefix_list, tls_enabled=False)
