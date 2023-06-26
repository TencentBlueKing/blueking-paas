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

"""Manage logics related with how to expose an application
"""
import logging
from typing import Dict, List, Optional

from paas_wl.networking.entrance.addrs import Address, EnvAddresses, EnvExposedURL
from paas_wl.networking.entrance.constants import AddressType
from paas_wl.networking.entrance.handlers import refresh_module_domains
from paas_wl.workloads.processes.controllers import env_is_running
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module
from paasng.publish.entrance.utils import get_legacy_url

logger = logging.getLogger(__name__)


def env_is_deployed(env: ModuleEnvironment) -> bool:
    """Return the deployed status(aka "is_running") of an environment object"""
    return get_live_addresses(env.module).get_is_running(env.environment)


def get_module_exposed_links(module: Module) -> Dict[str, Dict]:
    """Get exposed links of module's all environments

    - Support both cloud-native and default applications
    """
    links = {}
    for env in module.get_envs():
        deployed = env_is_deployed(env)
        if deployed:
            url_obj = get_exposed_url(env)
            url = url_obj.address if url_obj else None
        else:
            url = None
        links[env.environment] = {"deployed": deployed, "url": url}
    return links


def get_exposed_url(module_env: ModuleEnvironment) -> Optional[EnvExposedURL]:
    """Get exposed url object of given environment, if the environment is not
    running, return None instead.

    - Custom domain is not included
    - Both cloud-native and default application are supported

    :returns: Return the shortest url by default. If a preferred root domain was
        set and a match can be found using that domain, the matched address will
        be returned in priority.
    """
    addrs = get_addresses(module_env)
    if not addrs:
        return None

    # Use the first address because the results is sorted already
    addr = addrs[0]

    # Handle user preferred root domain, only available for built-in subdomains
    # and subpaths.
    if addr.type in ['subpath', 'subdomain']:
        if preferred_root := module_env.module.user_preferred_root_domain:
            # Find the first address ends with preferred root domain
            preferred_addr = next((a for a in addrs if a.hostname_endswith(preferred_root)), None)
            if not preferred_addr:
                logger.warning('No addresses found matching preferred root domain: %s', preferred_root)
            else:
                addr = preferred_addr
    return addr.to_exposed_url()


def get_addresses(env: ModuleEnvironment) -> 'List[Address]':
    """Get exposed addresses of an environment object, only built-in addresses
    is returned. This should be the main function for getting addresses of env.

    :returns: address items.
    """
    live_addrs = get_live_addresses(env.module)
    if not live_addrs.get_is_running(env.environment):
        return []

    # Get addresses by expose type
    module = env.module
    addrs: List[Address] = []
    if module.exposed_url_type == ExposedURLType.SUBPATH:
        addrs = live_addrs.get_addresses(env.environment, addr_type=AddressType.SUBPATH)
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        addrs = live_addrs.get_addresses(env.environment, addr_type=AddressType.SUBDOMAIN)
    elif module.exposed_url_type is None:
        url = get_legacy_url(env)
        addrs = [Address(type=AddressType.LEGACY, url=url)] if url else []
    return addrs


def list_custom_addresses(env: ModuleEnvironment) -> 'List[Address]':
    """List all custom addresses of given environment object, items will be
    returned even if the environment isn't running.
    """
    live_addrs = get_live_addresses(env.module)
    return live_addrs.get_addresses(env.environment, addr_type=AddressType.CUSTOM)


def list_module_custom_addresses(module: Module) -> 'List[Address]':
    """List all custom addresses of given module object, items will be
    returned even if environment isn't running.
    """
    live_addrs = get_live_addresses(module)
    return live_addrs.get_all_addresses(addr_type=AddressType.CUSTOM)


class ModuleLiveAddrs:
    """Stored a module's addresses and running status"""

    default_addr_type_ordering = ['subpath', 'subdomain', 'custom']

    def __init__(self, module: Module):
        self.module = module

    def get_is_running(self, env_name: str) -> bool:
        """Given running status of environment"""
        env = self.module.get_envs(env_name)
        return env_is_running(env)

    def get_addresses(self, env_name: str, addr_type: Optional[str] = None) -> List[Address]:
        """Return addresses of environment, the result was sorted, shorter and
        not reserved addresses are in front.

        :param addr_type: If given, include items whose type equal to this value
        """
        env = self.module.get_envs(env_name)
        addrs = EnvAddresses(env).get()
        if addr_type:
            addrs = [a for a in addrs if a.type == addr_type]
        self._sort_addrs(addrs)
        return addrs

    def get_all_addresses(self, addr_type: Optional[str] = None) -> List[Address]:
        """Return all addresses despite environment and running status

        :param addr_type: If given, include items whose type equal to this value
        """
        addrs = []
        for env in self.module.envs.all():
            addrs.extend(self.get_addresses(env_name=env.environment, addr_type=addr_type))
        self._sort_addrs(addrs)
        return addrs

    @classmethod
    def _sort_addrs(cls, items: List[Address]):
        """Sort a list of address objects"""
        # Make a map for sorting
        addr_type_ordering_map = {}
        for i, val in enumerate(cls.default_addr_type_ordering):
            addr_type_ordering_map[val] = i

        # Sort the addresses by below factors:
        # - type in the order of `default_addr_type_ordering`
        # - not reserved first
        # - shorter URL first
        items.sort(
            key=lambda addr: (
                addr_type_ordering_map.get(addr.type, float('inf')),
                addr.is_sys_reserved,
                len(addr.url),
            )
        )
        return items


def get_live_addresses(module: Module) -> ModuleLiveAddrs:
    return ModuleLiveAddrs(module)


# Exposed URL type related functions start
def update_exposed_url_type_to_subdomain(module: Module):
    """Update a module's exposed_url_type to subdomain"""
    # Return directly if exposed_url_type is already subdomain
    if module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        return

    module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
    module.save(update_fields=['exposed_url_type'])

    refresh_module_domains(module)

    # Also update app's address's in market if needed
    from paasng.publish.sync_market.handlers import sync_external_url_to_market

    sync_external_url_to_market(application=module.application)


# Exposed URL type related functions end
