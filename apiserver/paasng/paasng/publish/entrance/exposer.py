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
import itertools
import json
import logging
from typing import Dict, List, NamedTuple, Optional

from attrs import asdict, define
from django.conf import settings

from paasng.engine.constants import AppEnvName
from paasng.engine.controller.cluster import Cluster, get_region_cluster_helper
from paasng.engine.deploy.env_vars import env_vars_providers
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.helpers import get_module_clusters
from paasng.platform.modules.models import Module
from paasng.platform.region.models import get_region
from paasng.publish.entrance.domains import get_preallocated_domain, get_preallocated_domains_by_env
from paasng.publish.entrance.subpaths import get_preallocated_path, get_preallocated_paths_by_env
from paasng.publish.entrance.utils import URL
from paasng.publish.market.models import MarketConfig

logger = logging.getLogger(__name__)


class EnvExposedURL(NamedTuple):
    url: URL
    provider_type: str

    @property
    def address(self) -> str:
        return self.url.as_address()


def env_is_deployed(env: ModuleEnvironment) -> bool:
    """Return the deployed status(aka "is_running") of an environment object"""
    return get_deployed_status(env.module).get(env.environment, False)


def get_deployed_status(module: Module) -> Dict[str, bool]:
    """Return the deployed status(aka "is_running") of module's each environments

    :return: dict like {'stag': True, 'prod': False}
    """
    addrs = get_live_addresses(module)
    status = {
        'stag': addrs.get_is_running('stag'),
        'prod': addrs.get_is_running('prod'),
    }

    # Exclude archived environments
    # TODO: Remove this logic because archived applications's "is_running" should
    # be false naturally after workloads was updated.
    for env in module.envs.all():
        if env.is_offlined:
            status[env.environment] = False
    return status


def get_module_exposed_links(module: Module) -> Dict[str, Dict]:
    """Get exposed links of module's all environments

    - Support both cloud-native and default applications
    """
    links = {}
    deployed_statuses = get_deployed_status(module)
    for env in module.get_envs():
        status = deployed_statuses[env.environment]
        if status:
            url_obj = get_exposed_url(env)
            url = url_obj.address if url_obj else None
        else:
            url = None
        links[env.environment] = {"deployed": status, "url": url}
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


def get_market_address(application: Application) -> Optional[str]:
    """获取市场访问地址，兼容精简版应用。普通应用如未打开市场开关，返回 None"""
    region = get_region(application.region)
    addr = region.basic_info.link_production_app.format(code=application.code, region=application.region)
    if not application.engine_enabled:
        return addr

    # Only works for apps whose market config is enabled
    market_config, _ = MarketConfig.objects.get_or_create_by_app(application)
    if not market_config.enabled:
        return None
    return addr


def _get_legacy_url(env: ModuleEnvironment) -> Optional[str]:
    """Deprecated: Get legacy URL address which is a hard-coded value generated
    y region configuration.

    :return: None if not configured.
    """
    app = env.application
    if tmpl := get_region(app.region).basic_info.link_engine_app:
        return tmpl.format(code=app.code, region=app.region, name=env.engine_app.name)
    return None


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
        addrs = live_addrs.get_addresses(env.environment, addr_type='subpath')
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        addrs = live_addrs.get_addresses(env.environment, addr_type='subdomain')
    elif module.exposed_url_type is None:
        url = _get_legacy_url(env)
        addrs = [Address(type='legacy', url=url)] if url else []
    return addrs


def list_custom_addresses(env: ModuleEnvironment) -> 'List[Address]':
    """List all custom addresses of given environment object, items will be
    returned even if the environment isn't running.
    """
    # when user updates custom domain in "workloads" service, "apiserver" won't
    # be notified and cache won't be refreshed automatically, disable cache to
    # always get fresh data.
    live_addrs = get_live_addresses(env.module, no_cache=True)
    return live_addrs.get_addresses(env.environment, addr_type='custom')


def list_module_custom_addresses(module: Module) -> 'List[Address]':
    """List all custom addresses of given module object, items will be
    returned even if environment isn't running.
    """
    live_addrs = get_live_addresses(module)
    return live_addrs.get_all_addresses(addr_type='custom')


@define
class Address:
    """An simple struct stored application's URL address"""

    type: str
    url: str
    is_sys_reserved: bool = False

    def hostname_endswith(self, s: str) -> bool:
        """Check if current hostname ends with given string"""
        obj = URL.from_address(self.url)
        return obj.hostname.endswith(s)

    def to_exposed_url(self) -> EnvExposedURL:
        """To exposed URL object"""
        # INFO: Use self.type as "provider type" directly, this might need to be
        # changed in the future.
        return EnvExposedURL(url=URL.from_address(self.url), provider_type=self.type)


class ModuleLiveAddrs:
    """Stored a module's addresses and running status"""

    default_addr_type_ordering = ['subpath', 'subdomain', 'custom']

    def __init__(self, data: List[Dict]):
        self._data = data
        self._map_by_env = {}
        for item in data:
            self._map_by_env[item['env']] = item

    def get_is_running(self, env_name: str) -> bool:
        """Given running status of environment"""
        d = self._map_by_env.get(env_name, self._empty_item)
        return d['is_running']

    def get_addresses(self, env_name: str, addr_type: Optional[str] = None) -> List[Address]:
        """Return addresses of environment, the result was sorted, shorter and
        not reserved addresses are in front.

        :param addr_type: If given, include items whose type equal to this value
        """
        d = self._map_by_env.get(env_name, self._empty_item)
        addrs = d['addresses']
        if addr_type:
            addrs = [a for a in d['addresses'] if a['type'] == addr_type]
        items = [Address(**a) for a in addrs]
        self._sort_addrs(items)
        return items

    def get_all_addresses(self, addr_type: Optional[str] = None) -> List[Address]:
        """Return all addresses despite environment and running status

        :param addr_type: If given, include items whose type equal to this value
        """
        addrs = list(itertools.chain(*[d['addresses'] for d in self._map_by_env.values()]))
        if addr_type:
            addrs = [a for a in addrs if a['type'] == addr_type]
        items = [Address(**a) for a in addrs]
        self._sort_addrs(items)
        return items

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

    @property
    def _empty_item(self) -> Dict:
        """An empty item for handling default cases"""
        return {'is_running': False, 'addresses': []}


def get_live_addresses(module: Module, no_cache: bool = False) -> ModuleLiveAddrs:
    """Get addresses and is_running status for module's environments, result was
    cached for 1 minute by default.

    This is a low-level function, don't use it directly, use `get_addresses`
    instead.

    :param no_cache: Whether to disable cache, useful when caller requires fresh
        data, default to false.
    """
    # TODO: 修复循环依赖的问题
    from paas_wl.networking.ingress.addrs import EnvAddresses
    from paas_wl.workloads.processes.controllers import module_env_is_running

    results = []
    for env in module.get_envs():
        addrs = [asdict(obj) for obj in EnvAddresses(env).get()]
        results.append(
            {
                'env': env.environment,
                'is_running': module_env_is_running(env),
                'addresses': addrs,
            }
        )
    return ModuleLiveAddrs(results)


# pre-allocated addresses related functions start


def get_preallocated_url(module_env: ModuleEnvironment) -> Optional[EnvExposedURL]:
    """获取某环境的默认访问入口地址（不含独立域名)。

    - 地址为预计算生成，无需真实部署，不保证能访问
    """
    if items := get_preallocated_urls(module_env):
        return items[0]
    return None


def get_preallocated_urls(module_env: ModuleEnvironment) -> List[EnvExposedURL]:
    """获取某环境的所有可选访问入口地址（不含独立域名)。

    - 当集群配置了多个根域时，返回多个结果
    - 地址为预计算生成，无需真实部署，不保证能访问
    """
    module = module_env.module
    if module.exposed_url_type == ExposedURLType.SUBPATH:
        subpaths = get_preallocated_paths_by_env(module_env)
        return [EnvExposedURL(url=p.as_url(), provider_type='subpath') for p in subpaths]
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        domains = get_preallocated_domains_by_env(module_env)
        return [EnvExposedURL(url=d.as_url(), provider_type='subdomain') for d in domains]
    elif module.exposed_url_type is None:
        if url := _get_legacy_url(module_env):
            return [EnvExposedURL(url=URL.from_address(url), provider_type='legacy')]
    return []


@env_vars_providers.register_env
def _default_preallocated_urls(env: ModuleEnvironment) -> Dict[str, str]:
    """Append the default preallocated URLs, the value include both "stag" and "prod" environments
    for given module.
    """
    application = env.module.application
    clusters = get_module_clusters(env.module)
    addrs_value = ''
    try:
        addrs = get_preallocated_address(
            application.code, env.module.region, clusters=clusters, module_name=env.module.name
        )
        addrs_value = json.dumps(addrs._asdict())
    except ValueError:
        logger.warning('Fail to get preallocated address for application: %s, module: %s', application, env.module)
    return {settings.CONFIGVAR_SYSTEM_PREFIX + 'DEFAULT_PREALLOCATED_URLS': addrs_value}


class PreAddresses(NamedTuple):
    """Preallocated addresses, include both environments"""

    stag: str
    prod: str


def get_preallocated_address(
    app_code: str,
    region: Optional[str] = None,
    clusters: Optional[Dict[AppEnvName, Cluster]] = None,
    module_name: Optional[str] = None,
) -> PreAddresses:
    """Get the preallocated address for a application which was not released yet

    :param region: the region name on which the application will be deployed, if not given, use default region
    :param clusters: the env-cluster map, if not given, all use default cluster
    :param module_name: the module name, if not given, use default module
    :raises: ValueError no preallocated address can be found
    """
    region = region or settings.DEFAULT_REGION_NAME
    clusters = clusters or {}

    helper = get_region_cluster_helper(region)
    default_cluster = helper.get_default_cluster()
    stag_address, prod_address = "", ""

    # 生产环境
    prod_cluster = clusters.get(AppEnvName.PROD, default_cluster)
    prod_pre_subpaths = get_preallocated_path(app_code, prod_cluster.ingress_config, module_name=module_name)
    prod_pre_subdomains = get_preallocated_domain(app_code, prod_cluster.ingress_config, module_name=module_name)

    if prod_pre_subdomains:
        prod_address = prod_pre_subdomains.prod.as_url().as_address()

    # 若集群有子路径配置，则优先级高于子域名
    if prod_pre_subpaths:
        prod_address = prod_pre_subpaths.prod.as_url().as_address()

    # 测试环境
    stag_cluster = clusters.get(AppEnvName.STAG, default_cluster)
    stag_pre_subpaths = get_preallocated_path(app_code, stag_cluster.ingress_config, module_name=module_name)
    stag_pre_subdomains = get_preallocated_domain(app_code, stag_cluster.ingress_config, module_name=module_name)

    if stag_pre_subdomains:
        stag_address = stag_pre_subdomains.stag.as_url().as_address()

    # 若集群有子路径配置，则优先级高于子域名
    if stag_pre_subpaths:
        stag_address = stag_pre_subpaths.stag.as_url().as_address()

    if not (stag_address and prod_address):
        raise ValueError(
            "failed to get sub-path or sub-domain entrance config, "
            f"stag cluster: {stag_cluster.name}, prod cluster: {prod_cluster.name}"
        )

    return PreAddresses(stag=stag_address, prod=prod_address)


def get_bk_doc_url_prefix() -> str:
    """Obtain the address prefix of the BK Document Center,
    which is used for the product document address obtained by the app
    """
    if settings.BK_DOCS_URL_PREFIX:
        return settings.BK_DOCS_URL_PREFIX

    # Address for bk_docs_center saas
    # Remove the "/" at the end to ensure that the subdomain and subpath mode are handled in the same way
    return get_preallocated_address(settings.BK_DOC_APP_ID).prod.rstrip("/")


# pre-allocated addresses related functions end


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


def refresh_module_domains(module: Module):
    """Refresh a module's domains, you should call the function when module's exposed_url_type
    has been changed or application's default module was updated.
    """
    from paasng.engine.deploy.infras import AppDefaultDomains

    for env in module.envs.all():
        if not env.is_running():
            continue
        AppDefaultDomains(env).sync()


def refresh_module_subpaths(module: Module) -> None:
    """Refresh a module's subpaths, you should call the function when module's exposed_url_type
    has been changed or application's default module was updated.
    """
    from paasng.engine.deploy.infras import AppDefaultSubpaths

    for env in module.envs.all():
        if not env.is_running():
            continue
        AppDefaultSubpaths(env).sync()


# Exposed URL type related functions end
