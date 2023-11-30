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

from django.db import transaction

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.workloads.networking.ingress.certs import DomainWithCert, update_or_create_secret_by_cert
from paas_wl.workloads.networking.ingress.constants import AppDomainSource
from paas_wl.workloads.networking.ingress.entities import AutoGenDomain
from paas_wl.workloads.networking.ingress.exceptions import PersistentAppDomainRequired, ValidCertNotFound
from paas_wl.workloads.networking.ingress.kres_entities.ingress import PIngressDomain
from paas_wl.workloads.networking.ingress.managers.base import AppIngressMgr
from paas_wl.workloads.networking.ingress.models import AppDomain, Domain

logger = logging.getLogger(__name__)


@transaction.atomic()
def assign_custom_hosts(app: WlApp, domains: List[AutoGenDomain], default_service_name: str):
    """Assign custom_domains to app, may update multiple apps's Ingress resources
    if a domain's ownership has been changed from one app to another.

    :param domains: List of AutoGenDomain
    :param default_service_name: if ingress resource does not exist yet, use this service_name
        as default.
    :raise ValidCertNotFound: raise if any domain requires https, but the cert cannot be found
    """
    affected_apps = save_subdomains(app, domains)
    for app in affected_apps:
        logger.info("Syncing app %s's default ingress...", app.name)
        SubdomainAppIngressMgr(app).sync(default_service_name=default_service_name, delete_when_empty=True)


def save_subdomains(app: WlApp, domains: List[AutoGenDomain]) -> Set[WlApp]:
    """Save subdomains to database, return apps affected by this save operation.

    :param domains: List of AutoGenDomain
    """
    hosts = [domain.host for domain in domains]
    existed_domains = AppDomain.objects.filter(region=app.region, host__in=hosts, source=AppDomainSource.AUTO_GEN)
    affected_apps = {obj.app for obj in existed_domains}

    for domain in domains:
        obj, _ = AppDomain.objects.update_or_create(
            region=app.region,
            host=domain.host,
            defaults={"app": app, "source": AppDomainSource.AUTO_GEN, "https_enabled": domain.https_enabled},
        )
    # Remove domains which are no longer bound with app
    AppDomain.objects.filter(app=app, source=AppDomainSource.AUTO_GEN).exclude(host__in=hosts).delete()

    affected_apps.add(app)
    return affected_apps


class SubdomainAppIngressMgr(AppIngressMgr):
    """manage the ingress rule with individual subdomains"""

    def make_ingress_name(self) -> str:
        return f"{self.app.region}-{self.app.scheduler_safe_name}--direct"

    def list_desired_domains(self) -> List[PIngressDomain]:
        """List all desired domains for current app"""
        domains = []
        # Legacy custom domain
        config = self.app.latest_config
        if config.domain:
            domains.append(PIngressDomain(host=config.domain))

        factory = IngressDomainFactory(self.app)
        for d in AppDomain.objects.filter(app=self.app, source=AppDomainSource.AUTO_GEN):
            domains.append(factory.create(DomainWithCert.from_app_domain(d), raise_on_no_cert=False))
        return domains


class CustomDomainIngressMgr(AppIngressMgr):
    """Manager for custom domain"""

    CUSTOM_DOMAIN_PREFIX = "custom-"

    def __init__(self, domain: Domain):
        self.domain = domain
        super().__init__(domain.environment.wl_app)

    def make_ingress_name(self) -> str:
        """Make the name of Ingress resource

        :raise: PersistentAppDomainRequired when unable to generate ingress_name
        """
        if self.domain.has_customized_path_prefix():
            if not self.domain.id:
                raise PersistentAppDomainRequired(
                    '"id" field is required when generating name for Domain object with customized path_prefix'
                )

            # When path prefix is non-default, a different name is required to avoid conflict
            return f"{self.CUSTOM_DOMAIN_PREFIX}{self.domain.name}-{self.domain.id}"
        else:
            return f"{self.CUSTOM_DOMAIN_PREFIX}{self.domain.name}"

    def list_desired_domains(self) -> List[PIngressDomain]:
        factory = IngressDomainFactory(self.app)
        return [
            factory.create(
                DomainWithCert.from_custom_domain(region=self.app.region, domain=self.domain), raise_on_no_cert=False
            )
        ]


class IngressDomainFactory:
    """A factory class creates `PIngressDomain` objects"""

    def __init__(self, app: WlApp):
        self.app = app

    def create(self, app_domain: DomainWithCert, raise_on_no_cert: bool = True) -> PIngressDomain:
        """Detect domain scheme, return an ingress domain config

        :param app_domain: domain object stores in database
        :param raise_on_no_cert: when domain requires HTTPS and no valid cert can be found, raise
            `ValidCertNotFound`. If this argument is False, disable HTTPS instead.
        :return: `PIngressDomain` object which is ready for apply to cluster
        """
        path_prefix = app_domain.path_prefix
        if not app_domain.https_enabled:
            return PIngressDomain(host=app_domain.host, path_prefix_list=[path_prefix], tls_enabled=False)

        if app_domain.cert:
            secret_name, created = update_or_create_secret_by_cert(self.app, app_domain.cert)
            if created:
                logger.info("created a secret %s for host %s", secret_name, app_domain.host)

            return PIngressDomain(
                host=app_domain.host,
                path_prefix_list=[path_prefix],
                tls_enabled=app_domain.https_enabled,
                tls_secret_name=secret_name,
            )
        elif raise_on_no_cert:
            raise ValidCertNotFound("cannot enable https: no cert object found")
        else:
            # Disable HTTPS and write a warning message
            logger.warning("no valid cert can be found for domain: %s, disable HTTPS.", app_domain)
            return PIngressDomain(host=app_domain.host, path_prefix_list=[path_prefix], tls_enabled=False)
