# -*- coding: utf-8 -*-
import logging
from typing import Iterable, List, NamedTuple

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.constants import AppDomainSource
from paas_wl.networking.ingress.entities.ingress import PIngressDomain
from paas_wl.networking.ingress.exceptions import EmptyAppIngressError
from paas_wl.networking.ingress.models import AppDomain
from paas_wl.platform.applications.models import App
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

from .base import AppIngressMgr
from .domain import CustomDomainIngressMgr, SubdomainAppIngressMgr
from .subpath import SubPathAppIngressMgr

logger = logging.getLogger(__name__)


class UpdateTargetResult(NamedTuple):
    """Result type for `AppDefaultIngresses.safe_update_target`"""

    num_of_successful: int
    num_of_nonexistent: int


class AppDefaultIngresses:
    """helps managing app's default ingress rules."""

    def __init__(self, app: App):
        self.app = app

    def list(self) -> Iterable[AppIngressMgr]:
        """Return app's all default manger objects"""

        yield LegacyAppIngressMgr(self.app)
        yield SubdomainAppIngressMgr(self.app)
        yield SubPathAppIngressMgr(self.app)

        # Independent domain managers
        for domain in AppDomain.objects.filter(app=self.app, source=AppDomainSource.INDEPENDENT):
            yield CustomDomainIngressMgr(domain)

    def sync_ignore_empty(self, default_service_name: str = None):
        """Sync current ingress resources to apiserver,
        will not raise exceptions when any manager has no related domains.
        """
        for mgr in self.list():
            try:
                mgr.sync(default_service_name=default_service_name)
            except EmptyAppIngressError:
                pass

    def safe_update_target(self, service_name: str, service_port_name: str) -> UpdateTargetResult:
        """Update service target for all types of ingress, won't raise exception when ingress
        resource was not found——which might happen when Ingress resource is missing.

        For eg, if `cluster.ingress_config.sub_path_domains` was absent, the Ingress object
        for `SubPathAppIngressMgr` will never be created.

        :return: A result object with "num_of_successful" and "num_of_nonexistent" fields
        """
        num_of_successful, num_of_nonexistent = 0, 0
        for mgr in self.list():
            try:
                mgr.update_target(service_name, service_port_name)
            except AppEntityNotFound:
                logger.info('Ingress resource not found, skip updating target, manager: %s', mgr)
                num_of_nonexistent += 1
                continue
            else:
                num_of_successful += 1
        return UpdateTargetResult(num_of_successful, num_of_nonexistent)

    def delete_if_service_matches(self, service_name: str):
        """Delete all ingress resources if service name matches,
        will not raise exception when ingress resource was not found.
        """
        for mgr in self.list():
            try:
                legacy_ingress = mgr.get()
            except AppEntityNotFound:
                return

            # Only remove ingress when the service_name matches
            if legacy_ingress.service_name == service_name:
                mgr.delete()


class LegacyAppIngressMgr(AppIngressMgr):
    """manage the default legacy default ingress resource"""

    def make_ingress_name(self) -> str:
        return f'{self.app.region}-{self.app.scheduler_safe_name}'

    def list_desired_domains(self) -> List[PIngressDomain]:
        """List all desired domains for current app"""
        # The legacy default host
        cluster = get_cluster_by_app(self.app)
        domain_tmpl = cluster.ingress_config.default_ingress_domain_tmpl
        if not domain_tmpl:
            return []

        # Only write default ingress when `default_ingress_domain_tmpl` was not empty
        default_host = domain_tmpl % self.app.scheduler_safe_name_with_region
        return [PIngressDomain(host=default_host)]
