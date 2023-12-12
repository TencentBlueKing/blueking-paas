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
from paas_wl.bk_app.cnative.specs.constants import DomainGroupSource
from paas_wl.bk_app.cnative.specs.crd.domain_group_mapping import (
    Domain,
    DomainGroup,
    DomainGroupMapping,
    DomainGroupMappingSpec,
    MappingRef,
    ObjectMetadata,
)
from paas_wl.bk_app.cnative.specs.models import generate_bkapp_name
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.workloads.networking.ingress.certs import (
    DomainWithCert,
    pick_shared_cert,
    update_or_create_secret_by_cert,
)
from paas_wl.workloads.networking.ingress.constants import AppDomainSource
from paas_wl.workloads.networking.ingress.entities import AutoGenDomain
from paas_wl.workloads.networking.ingress.managers.domain import save_subdomains
from paas_wl.workloads.networking.ingress.managers.subpath import save_subpaths
from paas_wl.workloads.networking.ingress.models import AppDomain, AppSubpath
from paas_wl.workloads.networking.ingress.models import Domain as CustomDomain
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def save_addresses(env: ModuleEnvironment) -> Set[WlApp]:
    """Save an environment's pre-allocated addresses to database, includes both
    subdomains and subpaths.

    :return: Affected engine apps, "affected" means the app's domains or
        paths were updated during this save operation.
    """
    from paasng.platform.engine.configurations.ingress import AppDefaultDomains, AppDefaultSubpaths

    apps = set()
    domains = [AutoGenDomain(host=d.host, https_enabled=d.https_enabled) for d in AppDefaultDomains(env).domains]
    subpaths = [d.subpath for d in AppDefaultSubpaths(env).subpaths]
    apps.update(save_subdomains(env.wl_app, domains))
    apps.update(save_subpaths(env.wl_app, subpaths))
    return apps


class AddrResourceManager:
    """Manage kubernetes resources which was related with addresses"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.application = env.application
        self.wl_app = env.wl_app

    def build_mapping(self) -> DomainGroupMapping:
        """Build the mapping resource object"""
        # Make domain groups of all source types
        #
        # TODO: Handle "https_enabled" field, make a corresponding Secret resource
        # object
        subdomain_group = DomainGroup(sourceType=DomainGroupSource.SUBDOMAIN, domains=self._get_subdomain_domains())
        subpath_group = DomainGroup(sourceType=DomainGroupSource.SUBPATH, domains=self._get_subpath_domains())
        custom_group = DomainGroup(sourceType=DomainGroupSource.CUSTOM, domains=self._get_custom_domains())

        app_name = generate_bkapp_name(self.env)
        # Omit empty groups
        data = [subdomain_group, subpath_group, custom_group]
        data = [d for d in data if d.domains]
        return DomainGroupMapping(
            metadata=ObjectMetadata(name=self.wl_app.scheduler_safe_name),
            spec=DomainGroupMappingSpec(ref=MappingRef(name=app_name), data=data),
        )

    def _get_subdomain_domains(self) -> List[Domain]:
        """Get all "subdomain" source domain objects"""
        subdomains = AppDomain.objects.filter(app=self.wl_app, source=AppDomainSource.AUTO_GEN)
        return [to_domain(d) for d in subdomains]

    def _get_subpath_domains(self) -> List[Domain]:
        """Get all "subpath" source domain objects"""
        cluster = get_cluster_by_app(self.wl_app)
        root_domains = cluster.ingress_config.sub_path_domains
        if not root_domains:
            return []

        objs = AppSubpath.objects.filter(app=self.wl_app).order_by("created")
        paths = [obj.subpath for obj in objs]
        if not paths:
            return []

        return [
            to_shared_tls_domain(Domain(host=domain.name, pathPrefixList=paths), self.wl_app)
            for domain in root_domains
        ]

    def _get_custom_domains(self) -> List[Domain]:
        """Get all "custom" source domain objects"""
        custom_domains = CustomDomain.objects.filter(environment_id=self.env.id)
        # TODO: Add HTTPS support
        # Set "name" field to distinct Domains which shares same hostname, see CRD's docs for more details
        return [Domain(host=d.name, pathPrefixList=[d.path_prefix], name=str(d.pk)) for d in custom_domains]


def to_domain(d: AppDomain) -> Domain:
    """Turn a AppDomain object into Domain, a secret resource might be created
    during this process when HTTPS is enabled.

    :param d: AppDomain object, it might be updated if a shared cert was found
    """
    if not d.https_enabled:
        return Domain(host=d.host, pathPrefixList=["/"])

    domain = DomainWithCert.from_app_domain(d)
    if not domain.cert:
        # Disable HTTPS and write a warning message
        logger.warning("no valid cert can be found for domain: %s, disable HTTPS.", d)
        return Domain(host=d.host, pathPrefixList=["/"])

    secret_name, created = update_or_create_secret_by_cert(d.app, domain.cert)
    if created:
        logger.info("created a secret %s for host %s", secret_name, d.host)
    return Domain(host=d.host, pathPrefixList=["/"], tlsSecretName=secret_name)


def to_shared_tls_domain(d: Domain, app: WlApp) -> Domain:
    """Modify a domain object to make it support TLS, this is archived by finding
    matching shared cert and mutating "tlsSecretName" field.

    :return: The modified domain object
    """
    cert = pick_shared_cert(app.region, d.host)
    if not cert:
        d.tlsSecretName = None
        return d

    secret_name, created = update_or_create_secret_by_cert(app, cert)
    if created:
        logger.info("created a secret %s for host %s", secret_name, d.host)
    d.tlsSecretName = secret_name
    return d
