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
from itertools import groupby
from typing import Dict, List, NamedTuple, Optional

from django.conf import settings
from django.db.models import Count

from paasng.engine.constants import JobStatus
from paasng.engine.controller.cluster import Cluster, get_engine_app_cluster, get_region_cluster_helper
from paasng.engine.controller.shortcuts import make_internal_client
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.env_vars import env_vars_providers
from paasng.engine.models.deployment import Deployment
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module
from paasng.platform.region.models import get_region
from paasng.publish.entrance.domains import Domain, ModuleEnvDomains, get_preallocated_domain
from paasng.publish.entrance.subpaths import ModuleEnvSubpaths, Subpath, get_preallocated_path
from paasng.publish.entrance.utils import URL
from paasng.publish.market.models import MarketConfig

logger = logging.getLogger(__name__)


class EnvExposedURL(NamedTuple):
    url: URL
    provider_type: str

    @property
    def address(self) -> str:
        return self.url.as_address()


class BaseEnvExposedURLProvider:
    """Provides accessable URL address for environment"""

    provider_type: str = ''

    def __init__(self, module_env: ModuleEnvironment):
        self.env = module_env
        self.app = self.env.application

    def provide(self, include_no_running: bool = False) -> Optional[EnvExposedURL]:
        if not include_no_running and not self.env.is_running():
            return None

        url = self._provide_url()
        if url:
            return EnvExposedURL(url=url, provider_type=self.provider_type)
        return None

    def provide_all(self, include_no_running: bool = False) -> Optional[List[EnvExposedURL]]:
        if not include_no_running and not self.env.is_running():
            return None

        urls = self._provide_urls()
        if urls:
            return [EnvExposedURL(url=url, provider_type=self.provider_type) for url in urls]
        return None

    def _provide_url(self) -> Optional[URL]:
        """provide an accessable url, if current env does not match the pre-conditions,
        return None instead
        """
        raise NotImplementedError

    def _provide_urls(self) -> Optional[List[URL]]:
        """provide all accessable urls, if current env does not match the pre-conditions,
        return None instead
        """
        raise NotImplementedError

    def format_region_url_tmpl(self, tmpl) -> str:
        """Render an url template in region config"""
        context = {
            'code': self.app.code,
            'region': self.app.region,
            'name': self.env.engine_app.name,
        }
        return tmpl.format(**context)


class MarketURLProvider(BaseEnvExposedURLProvider):
    """URL Provider by market"""

    provider_type = 'market'

    def _provide_url(self) -> Optional[URL]:
        # Only works for "production" env
        if self.env.environment != AppEnvironment.PRODUCTION.value:
            return None

        # Only works for apps whose market config is enabled
        market_config, _ = MarketConfig.objects.get_or_create_by_app(self.app)
        if not (market_config.enabled and market_config.source_module == self.env.module):
            return None

        region = get_region(self.app.region)
        return URL.from_address(self.format_region_url_tmpl(region.basic_info.link_production_app))

    def _provide_urls(self) -> Optional[List[URL]]:
        address = self._provide_url()
        if not address:
            return None
        return [address]


class SubDomainURLProvider(BaseEnvExposedURLProvider):
    """The default URL for application environments"""

    provider_type = 'default_subdomain'

    def _provide_url(self) -> Optional[URL]:
        if self.env.module.exposed_url_type != ExposedURLType.SUBDOMAIN:
            return None

        helper = ModuleEnvDomains(self.env)
        domains = helper.all()
        user_preferred = helper.make_user_preferred_one()

        if not domains:
            return None

        if user_preferred:
            return user_preferred.as_url()

        domains = sorted(domains, key=Domain.sort_by_type, reverse=True)
        return domains[0].as_url()

    def _provide_urls(self) -> Optional[List[URL]]:
        if self.env.module.exposed_url_type != ExposedURLType.SUBDOMAIN:
            return None

        domains = ModuleEnvDomains(self.env).all()
        if not domains:
            return None

        domains = sorted(domains, key=Domain.sort_by_type, reverse=True)
        _, group = next(groupby(domains, key=Domain.sort_by_type))
        return [domain.as_url() for domain in group]


class SubPathURLProvider(BaseEnvExposedURLProvider):
    """Provides sub path URL for module environments.

    To make subpath address available:

    - 'sub_path_domains' must be configured in region's `ingress_config` config object
    - the module's exposed_url_type must be 'subpath' (by default, `expose_type` was set to region's default value
      when module was created)
    """

    provider_type = 'subpath'

    def _provide_url(self) -> Optional[URL]:
        if self.env.module.exposed_url_type != ExposedURLType.SUBPATH:
            return None

        helper = ModuleEnvSubpaths(self.env)
        subpaths = helper.all()
        user_preferred = helper.make_user_preferred_one()

        if not subpaths:
            return None

        if user_preferred:
            return user_preferred.as_url()

        subpaths = sorted(subpaths, key=Subpath.sort_by_type, reverse=True)
        return subpaths[0].as_url()

    def _provide_urls(self) -> Optional[List[URL]]:
        if self.env.module.exposed_url_type != ExposedURLType.SUBPATH:
            return None

        subpaths = ModuleEnvSubpaths(self.env).all()
        if not subpaths:
            return None

        # Pick addresses which have the biggest "type" by value, see
        # `SubpathPriorityType` for more details.
        subpaths = sorted(subpaths, key=Subpath.sort_by_type, reverse=True)
        _, group = next(groupby(subpaths, key=Subpath.sort_by_type))
        return [subpath.as_url() for subpath in group]


class LegacyEngineURLProvider(BaseEnvExposedURLProvider):
    """Deprecated: legacy URL address"""

    provider_type = 'legacy'

    def _provide_url(self) -> Optional[URL]:
        region = get_region(self.app.region)
        return URL.from_address(self.format_region_url_tmpl(region.basic_info.link_engine_app))

    def _provide_urls(self) -> Optional[List[URL]]:
        address = self._provide_url()
        if not address:
            return None
        return [address]


def get_deployed_status(module: Module) -> Dict[str, bool]:
    """Return the deployed status(aka "is_running") of module's each environments

    :return: dict like {'stag': True, 'prod': False}
    """
    envs = module.envs.all()
    ret = {}
    # Exclude offlined envs
    for env in envs:
        if env.is_offlined:
            ret[env.environment] = False

    # Query succeeded deployments count for all environments
    envs = [env for env in envs if env.environment not in ret]
    counter_by_env = dict(
        Deployment.objects.filter(app_environment__in=envs, status=JobStatus.SUCCESSFUL.value)
        .values_list('app_environment')
        .annotate(total=Count('app_environment'))
        .order_by('total')
    )
    for env in envs:
        ret[env.environment] = counter_by_env.get(env.pk, 0) > 0
    return ret


def get_module_exposed_links(module: Module) -> Dict[str, Dict]:
    """Get exposed links of module's all environments"""
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
    """Get exposed url of given module environment

    :returns: None if no url can be found
    """
    providers = [
        # Market URL has the highest priority
        MarketURLProvider(module_env),
        SubPathURLProvider(module_env),
        SubDomainURLProvider(module_env),
        LegacyEngineURLProvider(module_env),
    ]
    for provider in providers:
        url = provider.provide()
        if url:
            return url
    return None


def get_default_access_entrance(
    module_env: ModuleEnvironment, include_no_running: bool = False
) -> Optional[EnvExposedURL]:
    """返回模块在对应环境下的默认访问入口(由平台提供的)

    :returns: None if no url can be found
    """
    providers = [
        SubPathURLProvider(module_env),
        SubDomainURLProvider(module_env),
        LegacyEngineURLProvider(module_env),
    ]
    for provider in providers:
        url = provider.provide(include_no_running)
        if url:
            return url
    return None


def get_default_access_entrances(
    module_env: ModuleEnvironment, include_no_running: bool = False
) -> Optional[List[EnvExposedURL]]:
    """返回模块在对应环境下的所有可选的默认访问入口(由平台提供的)

    :returns: None if no url can be found
    """
    providers = [
        SubPathURLProvider(module_env),
        SubDomainURLProvider(module_env),
        LegacyEngineURLProvider(module_env),
    ]
    for provider in providers:
        urls = provider.provide_all(include_no_running)
        if urls:
            return urls
    return None


def get_market_address(application: Application) -> Optional[str]:
    """获取市场访问地址，兼容精简版应用"""
    if not application.engine_enabled:
        region = get_region(application.region)
        context = {
            'code': application.code,
            'region': application.region,
        }
        return region.basic_info.link_production_app.format(**context)

    exposed_url = MarketURLProvider(application.get_default_module().get_envs("prod")).provide()
    if exposed_url:
        return exposed_url.address
    return None


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


class ModuleLiveAddrs:
    """Stored a module's addresses and running status"""

    # An empty item for handling default cases
    _empty_item = {'is_running': False, 'addresses': []}

    def __init__(self, data: List[Dict]):
        self._data = data
        self._map_by_env = {}
        for item in data:
            self._map_by_env[item['env']] = item

    def get_is_running(self, env_name: str) -> bool:
        """Given running status of environment"""
        d = self._map_by_env.get(env_name, self._empty_item)
        return d['is_running']

    def get_addresses(self, env_name: str) -> List[Dict]:
        """Given addresses of environment"""
        d = self._map_by_env.get(env_name, self._empty_item)
        return d['addresses']


def get_live_addresses(module: Module) -> ModuleLiveAddrs:
    """Get addresses and is_running status for module's environments."""
    data = make_internal_client().list_env_addresses(module.application.code, module.name)
    return ModuleLiveAddrs(data)


def get_module_exposed_links_live(module: Module) -> Dict[str, Dict]:
    """Get exposed links of module's all environments.

    This is the "live" version of the original `get_module_exposed_links` function,
    key differences:

    - Support both cloud-native and default applications
    - market URL and user-preferred addresses not considered

    The goal is to replace `get_module_exposed_links`(and other related *Providers)
    with this function in the future.
    """
    links = {}
    addrs = get_live_addresses(module)
    for env in module.get_envs():
        if items := addrs.get_addresses(env.environment):
            # TODO: Pick url by priority order in the future
            url = items[0]['url']
        else:
            url = None
        links[env.environment] = {"deployed": addrs.get_is_running(env.environment), "url": url}
    return links


def get_exposed_url_live(env: ModuleEnvironment) -> Optional[EnvExposedURL]:
    """Get exposed url of given module environment.

    This is the "live" version of the original `get_exposed_url` function, key
    differences:

    - Support both cloud-native and default applications
    - market URL and user-preferred addresses not included

    :returns: None if no url can be found
    """
    addrs = get_live_addresses(env.module)
    if items := addrs.get_addresses(env.environment):
        # TODO: Pick url by priority order in the future
        return EnvExposedURL(url=URL.from_address(items[0]['url']), provider_type='live')
    return None
