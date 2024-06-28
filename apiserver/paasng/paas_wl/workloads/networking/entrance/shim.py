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

import logging
from typing import List, Optional, Tuple

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.core.env import env_is_running
from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.networking.entrance.addrs import URL, Address
from paas_wl.workloads.networking.entrance.allocator.domains import ModuleEnvDomains
from paas_wl.workloads.networking.entrance.allocator.subpaths import ModuleEnvSubpaths
from paas_wl.workloads.networking.entrance.constants import AddressType
from paas_wl.workloads.networking.ingress.constants import AppDomainSource
from paas_wl.workloads.networking.ingress.models import AppDomain, AppSubpath, Domain
from paasng.core.region.models import get_region
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType

logger = logging.getLogger(__name__)


def get_legacy_url(env: ModuleEnvironment) -> Optional[str]:
    """Deprecated: Get legacy URL address which is a hard-coded value generated
    y region configuration.

    :return: None if not configured.
    """
    app = env.application
    if tmpl := get_region(app.region).basic_info.link_engine_app:
        return tmpl.format(code=app.code, region=app.region, name=env.engine_app.name)
    return None


class BaseEnvAddresses:
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

    def list(self) -> List[Address]:
        """Get all addresses"""
        raise NotImplementedError

    def list_subdomain(self) -> List[Address]:
        """list all subdomain addresses for given environment"""
        raise NotImplementedError

    def list_subpath(self) -> List[Address]:
        """list all subpath addresses for given environment"""
        raise NotImplementedError

    def list_legacy(self) -> List[Address]:
        """Get addresses by legacy logic"""
        url = get_legacy_url(self.env)
        return [Address(type=AddressType.LEGACY, url=url)] if url else []

    def list_custom(self) -> List[Address]:
        """Get addresses from custom domains"""
        custom_domains = Domain.objects.filter(environment_id=self.env.id)
        return self._sort(
            [
                Address(AddressType.CUSTOM, self._make_url(d.https_enabled, d.name, d.path_prefix), id=d.id)
                for d in custom_domains
            ]
        )

    def has_custom_url(self, url: str) -> bool:
        """check whether the given url is a custom domain in the environment"""
        return any(addr.url == url for addr in self.list_custom())

    def _make_url(self, https_enabled: bool, host: str, path: str = "/") -> str:
        """Make URL address"""
        protocol = "https" if https_enabled else "http"
        port = self.ingress_cfg.port_map.get_port_num(protocol)
        return URL(protocol, hostname=host, port=port, path=path).as_address()

    @staticmethod
    def _sort(addrs: List[Address]) -> List[Address]:
        """Sort address list, short and not reserved address first"""
        return sorted(addrs, key=lambda addr: (addr.is_sys_reserved, len(addr.url)))


class LiveEnvAddresses(BaseEnvAddresses):
    """Get all live addresses for given environment

    **live** means that the address should currently be accessible.
    """

    def list(self) -> List[Address]:
        """list all `live` addresses for deployed environment"""
        if not env_is_running(self.env):
            return []

        return self.list_subdomain() + self.list_subpath() + self.list_custom() + self.list_legacy()

    def list_subdomain(self) -> List[Address]:
        """list all `live` subdomain addresses for deployed environment"""
        subdomains = AppDomain.objects.filter(app=self.wl_app, source=AppDomainSource.AUTO_GEN)
        addrs = []
        for d in subdomains:
            root_domain = self.ingress_cfg.find_app_root_domain(d.host)
            is_sys_reserved = root_domain.reserved if root_domain else False
            addrs.append(Address(AddressType.SUBDOMAIN, self._make_url(d.https_enabled, d.host), is_sys_reserved))
        return self._sort(addrs)

    def list_subpath(self) -> List[Address]:
        """list all `activated` subpath for deployed environment"""
        path_objs = AppSubpath.objects.filter(app=self.wl_app).order_by("created")
        addrs = []
        for domain in self.ingress_cfg.sub_path_domains:
            for obj in path_objs:
                url = self._make_url(domain.https_enabled, domain.name, obj.subpath)
                addrs.append(Address(AddressType.SUBPATH, url, domain.reserved))
        return self._sort(addrs)


class PreAllocatedEnvAddresses(BaseEnvAddresses):
    """Get all pre-allocated addresses for given environment

    **pre-allocated** means that the address should be allocated to the given env,
    But the address may not currently accessible if the given env is not deployed.
    """

    def list(self) -> List[Address]:
        return self.list_subdomain() + self.list_subpath() + self.list_custom() + self.list_legacy()

    def list_subdomain(self) -> List[Address]:
        """list all subdomain addresses which should be allocated to the given environment"""
        subdomains = ModuleEnvDomains(self.env).all()
        return self._sort([Address(type=AddressType.SUBDOMAIN, url=d.as_url().as_address()) for d in subdomains])

    def list_subpath(self) -> List[Address]:
        """list all subpath addresses which should be allocated to the given environment"""
        subpaths = ModuleEnvSubpaths(self.env).all()
        return self._sort([Address(type=AddressType.SUBPATH, url=p.as_url().as_address()) for p in subpaths])


def get_builtin_addr_preferred(env: ModuleEnvironment) -> Tuple[bool, Optional[Address]]:
    """Get the highest priority builtin address of given environment

    - Custom domain is not included
    - Both cloud-native and default application are supported

    :return: Tuple[bool, str] containing two values:
        - A boolean value indicating whether the address is living.
        - A string representing the shortest URL by default.
          * If a preferred root domain was set and a match can be found using that domain,
          * the matched address will be returned in priority.
          * If the env is not running, the URL returned is algorithmically allocated(MAY NOT accessible).
    """
    module = env.module
    is_living, addresses = get_builtin_addrs(env)
    if not addresses:
        return is_living, None

    # Use the first address because the results is sorted already
    addr = addresses[0]
    if module.exposed_url_type in [ExposedURLType.SUBPATH, ExposedURLType.SUBDOMAIN] and (
        preferred_root := module.user_preferred_root_domain
    ):
        # Find the first address ends with preferred root domain
        preferred_addr = next((a for a in addresses if a.hostname_endswith(preferred_root)), None)
        if not preferred_addr:
            logger.warning("No addresses found matching preferred root domain: %s", preferred_root)
        else:
            addr = preferred_addr
    return is_living, addr


def get_builtin_addrs(env: ModuleEnvironment) -> Tuple[bool, List[Address]]:
    """Get all builtin addresses of given environment

    :returns: Tuple[bool, str] containing two values:
        - A boolean value indicating whether the addresses are living
        - A string representing the shortest URL by default.
          * If a preferred root domain was set and a match can be found using that domain,
          * the matched address will be returned in priority.
          * If the env is not running, the URLs returned are algorithmically allocated(MAY NOT accessible).
    """
    module = env.module
    svc: BaseEnvAddresses
    is_living = env_is_running(env)
    if is_living:
        svc = LiveEnvAddresses(env)
    else:
        svc = PreAllocatedEnvAddresses(env)
    if module.exposed_url_type == ExposedURLType.SUBPATH:
        addresses = svc.list_subpath()
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        addresses = svc.list_subdomain()
    else:
        addresses = svc.list_legacy()
    return is_living, addresses
