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
from typing import List, Optional, Tuple

from paas_wl.cluster.shim import EnvClusterService
from paas_wl.networking.entrance.addrs import URL, Address
from paas_wl.networking.entrance.allocator.domains import ModuleEnvDomains
from paas_wl.networking.entrance.allocator.subpaths import ModuleEnvSubpaths
from paas_wl.networking.entrance.constants import AddressType
from paas_wl.networking.ingress.constants import AppDomainSource
from paas_wl.networking.ingress.models import AppDomain, AppSubpath, Domain
from paas_wl.platform.applications.models import WlApp
from paas_wl.workloads.processes.controllers import env_is_running
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.region.models import get_region


def get_legacy_url(env: ModuleEnvironment) -> Optional[str]:
    """Deprecated: Get legacy URL address which is a hard-coded value generated
    y region configuration.

    :return: None if not configured.
    """
    app = env.application
    if tmpl := get_region(app.region).basic_info.link_engine_app:
        return tmpl.format(code=app.code, region=app.region, name=env.engine_app.name)
    return None


class EnvAddresses:
    """Get all addresses for given environment"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.application = env.application
        self.module = env.module

    @property
    def wl_app(self):
        return WlApp.objects.get(pk=self.env.engine_app_id)

    @property
    def ingress_cfg(self):
        return EnvClusterService(self.env).get_cluster().ingress_config

    def list_by_allocator(self) -> List[Address]:
        """list all addresses which should be allocated to the given environment"""
        return (
            self.list_subdomain_by_allocator()
            + self.list_subpath_by_allocator()
            + self.list_custom()
            + self.list_legacy()
        )

    def list_subdomain_by_allocator(self) -> List[Address]:
        """list all subdomain addresses which should be allocated to the given environment"""
        subdomains = ModuleEnvDomains(self.env).all()
        return self._sort([Address(type=AddressType.SUBDOMAIN, url=d.as_url().as_address()) for d in subdomains])

    def list_subpath_by_allocator(self) -> List[Address]:
        """list all subpath addresses which should be allocated to the given environment"""
        subpaths = ModuleEnvSubpaths(self.env).all()
        return self._sort([Address(type=AddressType.SUBPATH, url=p.as_url().as_address()) for p in subpaths])

    def list_activated(self) -> List[Address]:
        """"list all `activated` addresses for deployed environment"""
        if not env_is_running(self.env):
            return []

        return (
            self.list_activated_subdomain()
            + self.list_activated_subpath()
            + self._sort(self.list_custom())
            + self.list_legacy()
        )

    def list_activated_subdomain(self) -> List[Address]:
        """list all `activated` subdomain addresses for deployed environment"""
        subdomains = AppDomain.objects.filter(app=self.wl_app, source=AppDomainSource.AUTO_GEN)
        addrs = []
        for d in subdomains:
            root_domain = self.ingress_cfg.find_app_root_domain(d.host)
            is_sys_reserved = root_domain.reserved if root_domain else False
            addrs.append(Address(AddressType.SUBDOMAIN, self._make_url(d.https_enabled, d.host), is_sys_reserved))
        return self._sort(addrs)

    def list_activated_subpath(self) -> List[Address]:
        """list all `activated` subpath for deployed environment"""
        path_objs = AppSubpath.objects.filter(app=self.wl_app).order_by('created')
        addrs = []
        for domain in self.ingress_cfg.sub_path_domains:
            for obj in path_objs:
                url = self._make_url(domain.https_enabled, domain.name, obj.subpath)
                addrs.append(Address(AddressType.SUBPATH, url, domain.reserved))
        return self._sort(addrs)

    def list_custom(self) -> List[Address]:
        """Get addresses from custom domains"""
        custom_domains = Domain.objects.filter(environment_id=self.env.id)
        return [
            Address(AddressType.CUSTOM, self._make_url(d.https_enabled, d.name, d.path_prefix), id=d.id)
            for d in custom_domains
        ]

    def validate_custom_url(self, url: str) -> bool:
        """validate if the given url is a custom domain url"""
        for addr in self.list_custom():
            if addr.url == url:
                return True
        return False

    def list_legacy(self) -> List[Address]:
        """Get addresses by legacy logic"""
        url = get_legacy_url(self.env)
        return [Address(type=AddressType.LEGACY, url=url)] if url else []

    def _make_url(self, https_enabled: bool, host: str, path: str = '/') -> str:
        """Make URL address"""
        protocol = "https" if https_enabled else "http"
        port = self.ingress_cfg.port_map.get_port_num(protocol)
        return URL(protocol, hostname=host, port=port, path=path).as_address()

    @staticmethod
    def _sort(addrs: List[Address]) -> List[Address]:
        """Sort address list, short and not reserved address first"""
        return sorted(addrs, key=lambda addr: (addr.is_sys_reserved, len(addr.url)))


logger = logging.getLogger(__name__)


def get_highest_priority_builtin_address(env: ModuleEnvironment) -> Tuple[bool, Optional[Address]]:
    """Get the highest priority builtin address of given environment

    - Custom domain is not included
    - Both cloud-native and default application are supported

    :returns: Return the shortest url by default. If a preferred root domain was
        set and a match can be found using that domain, the matched address will
        be returned in priority.
    """
    module = env.module
    is_running, addresses = get_builtin_addresses(env)
    if not addresses:
        return is_running, None
    addr = addresses[0]
    if module.exposed_url_type in [ExposedURLType.SUBPATH, ExposedURLType.SUBDOMAIN]:
        if preferred_root := module.user_preferred_root_domain:
            # Find the first address ends with preferred root domain
            preferred_addr = next((a for a in addresses if a.hostname_endswith(preferred_root)), None)
            if not preferred_addr:
                logger.warning('No addresses found matching preferred root domain: %s', preferred_root)
            else:
                addr = preferred_addr
    return is_running, addr


def get_builtin_addresses(env: ModuleEnvironment) -> Tuple[bool, List[Address]]:
    """Get all builtin address of given environment"""
    module = env.module
    svc = EnvAddresses(env)
    is_running = env_is_running(env)
    if module.exposed_url_type == ExposedURLType.SUBPATH:
        addresses = svc.list_activated_subpath() if is_running else svc.list_subpath_by_allocator()
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        addresses = svc.list_activated_subdomain() if is_running else svc.list_subdomain_by_allocator()
    else:
        addresses = svc.list_legacy()
    return is_running, addresses
