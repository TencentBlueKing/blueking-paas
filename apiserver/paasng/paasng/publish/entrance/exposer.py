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
import json
import logging
from typing import Dict, List, NamedTuple, Optional

from attrs import define
from django.conf import settings

from paasng.engine.controller.cluster import Cluster, get_engine_app_cluster, get_region_cluster_helper
from paasng.engine.controller.shortcuts import make_internal_client
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.env_vars import env_vars_providers
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module
from paasng.platform.region.models import get_region
from paasng.publish.entrance.domains import ModuleEnvDomains, get_preallocated_domain, get_preallocated_domains_by_env
from paasng.publish.entrance.subpaths import ModuleEnvSubpaths, get_preallocated_path, get_preallocated_paths_by_env
from paasng.publish.entrance.utils import URL
from paasng.publish.market.models import MarketConfig

logger = logging.getLogger(__name__)


class EnvExposedURL(NamedTuple):
    url: URL
    provider_type: str

    @property
    def address(self) -> str:
        return self.url.as_address()


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

    # Use the first address because the results have been sorted by length already
    addr = addrs[0]

    # Handle user preferred root domain, only available for built-in subdomains
    # and subpaths.
    if addrs[0].type in ['subpath', 'subdomain']:
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

    :returns: address items sorted by URL length, empty list if env has not been
        deployed yet.
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

    addrs.sort(key=lambda a: len(a.url))
    return addrs


# TODO: Add `def get_addresses_with_custom` function which include custom domains.


@define
class Address:
    """An simple struct stored application's URL address"""

    type: str
    url: str

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
        """Given addresses of environment

        :param addr_type: If given, include items whose type equal to this value
        """
        d = self._map_by_env.get(env_name, self._empty_item)
        addrs = d['addresses']
        if addr_type:
            addrs = [a for a in d['addresses'] if a['type'] == addr_type]
        return [Address(**a) for a in addrs]

    @property
    def _empty_item(self) -> Dict:
        """An empty item for handling default cases"""
        return {'is_running': False, 'addresses': []}


def get_live_addresses(module: Module) -> ModuleLiveAddrs:
    """Get addresses and is_running status for module's environments.

    This is a low-level function, don't use it directly, use `get_addresses`
    instead.
    """
    data = make_internal_client().list_env_addresses(module.application.code, module.name)
    return ModuleLiveAddrs(data)


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
    cluster = get_engine_app_cluster(application.region, env.get_engine_app().name)
    addrs_value = ''
    try:
        addrs = get_preallocated_address(
            application.code, application.region, cluster=cluster, module_name=env.module.name
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
    app_code: str, region: Optional[str] = None, cluster: Optional[Cluster] = None, module_name: Optional[str] = None
) -> PreAddresses:
    """Get the preallocated address for a application which was not released yet

    :param region: the region name on which the application will be deployed, if not given, use default region
    :param cluster: the cluster object, if not given, use default cluster
    :param module: the module name, if not given, use default module
    :raises: ValueError no preallocated address can be found
    """
    region = region or settings.DEFAULT_REGION_NAME
    helper = get_region_cluster_helper(region)
    if not cluster:
        cluster = helper.get_default_cluster()

    ingress_config = cluster.ingress_config
    pre_subpaths = get_preallocated_path(app_code, ingress_config, module_name=module_name)
    if pre_subpaths:
        return PreAddresses(
            stag=pre_subpaths.stag.as_url().as_address(),
            prod=pre_subpaths.prod.as_url().as_address(),
        )

    pre_subdomains = get_preallocated_domain(app_code, ingress_config, module_name=module_name)
    if pre_subdomains:
        return PreAddresses(
            stag=pre_subdomains.stag.as_url().as_address(),
            prod=pre_subdomains.prod.as_url().as_address(),
        )
    raise ValueError(f'No sub-path or sub-domain entrance config was configured for cluster: "{cluster.name}"')


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
    for env in module.envs.all():
        if not env.is_running():
            continue

        logger.info(f"updating {env.engine_app.name}'s exposed_url_type to subdomain...")
        engine_client = EngineDeployClient(env.engine_app)
        domains = [d.as_dict() for d in ModuleEnvDomains(env).all()]
        engine_client.update_domains(domains)


def refresh_module_subpaths(module: Module) -> None:
    """Refresh a module's subpaths, you should call the function when module's exposed_url_type
    has been changed or application's default module was updated.
    """
    for env in module.envs.all():
        if not env.is_running():
            continue

        logger.info(f"refreshing {env.engine_app.name}'s subpaths...")
        engine_client = EngineDeployClient(env.engine_app)
        subpaths = [d.as_dict() for d in ModuleEnvSubpaths(env).all()]
        engine_client.update_subpaths(subpaths)


# Exposed URL type related functions end
