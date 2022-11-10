# -*- coding: utf-8 -*-
import logging
from typing import Dict, List, Set

from django.conf import settings

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.certs.utils import pick_shared_cert, update_or_create_secret_by_cert
from paas_wl.networking.ingress.constants import AppSubpathSource
from paas_wl.networking.ingress.entities.ingress import PIngressDomain
from paas_wl.networking.ingress.models import AppSubpath
from paas_wl.platform.applications.models import App

from .base import AppIngressMgr
from .common import SubpathCompatPlugin

logger = logging.getLogger(__name__)


def assign_subpaths(app: App, subpaths: List[str], default_service_name: str):
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


def save_subpaths(app: App, subpaths: List[str]) -> Set[App]:
    """Save subpaths to database, return apps affected by this save operation.

    :param subpaths: List of subpaths
    """
    existed_subpaths = AppSubpath.objects.filter(
        region=app.region, subpath__in=subpaths, source=AppSubpathSource.DEFAULT
    )
    affected_apps = set(obj.app for obj in existed_subpaths)

    for subpath in subpaths:
        AppSubpath.objects.update_or_create(
            region=app.region, subpath=subpath, defaults={'app': app, 'source': AppSubpathSource.DEFAULT}
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

    plugins = [SubpathCompatPlugin]

    def make_ingress_name(self) -> str:
        return f'{self.app.region}-{self.app.scheduler_safe_name}--subpath'

    def list_desired_domains(self) -> List[PIngressDomain]:
        """List all desired domains for current app"""
        cluster = get_cluster_by_app(self.app)
        domains = cluster.ingress_config.sub_path_domains
        if not domains:
            logger.info('sub-path domain was not configured for cluster, return empty result')
            return []

        path_objs = AppSubpath.objects.filter(app=self.app).order_by('created')
        paths = [obj.subpath for obj in path_objs]
        if not paths:
            return []

        return [self.create_ingress_domain(domain.name, paths, domain.https_enabled) for domain in domains]

    def get_annotations(self) -> Dict:
        annotations = {}

        # 当有多个 ingress controller 存在时，可以指定需要使用的链路
        if settings.APP_INGRESS_CLASS is not None:
            annotations["kubernetes.io/ingress.class"] = settings.APP_INGRESS_CLASS

        return annotations

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
            logger.warning('no valid cert can be found for domain: %s, disable HTTPS.', host)
            return PIngressDomain(host=host, path_prefix_list=path_prefix_list, tls_enabled=False)
