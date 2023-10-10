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
"""Subpaths management"""
from dataclasses import dataclass, field
from operator import attrgetter
from typing import Dict, List, Optional

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.conf import settings

from paas_wl.cluster.models import Domain as DomainCfg
from paas_wl.cluster.models import IngressConfig, PortMap
from paas_wl.cluster.shim import EnvClusterService
from paas_wl.networking.entrance.addrs import URL
from paas_wl.networking.entrance.utils import to_dns_safe
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.applications.models import ModuleEnvironment


class SubpathPriorityType(int, StructuredEnum):
    STABLE = EnumField(1, label="无缩写")
    WITHOUT_MODULE = EnumField(2, label="无模块，指向主模块")
    ONLY_CODE = EnumField(3, label="无模块无环境，指向主模块生产环境")


@dataclass
class Subpath:
    """A subpath object"""

    subpath: str
    host: str
    https_enabled: bool = False
    type: int = SubpathPriorityType.STABLE
    port_map: PortMap = field(default_factory=PortMap)

    def as_url(self) -> URL:
        protocol = "https" if self.https_enabled else "http"
        port = self.port_map.get_port_num(protocol)
        return URL(
            protocol=protocol,
            hostname=self.host,
            port=port,
            path=self.subpath,
        )

    def as_dict(self) -> Dict:
        return {'subpath': self.subpath, 'host': self.host, 'https_enabled': self.https_enabled}

    @staticmethod
    def sort_by_len(subpath: 'Subpath'):
        # ignore protocol size
        url = subpath.as_url()
        url.protocol = "http"
        return len(url.as_address())

    @staticmethod
    def sort_by_type(subpath: 'Subpath'):
        return subpath.type


class ModuleEnvSubpaths:
    """managing subpaths for module environment"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.application = env.module.application
        self.ingress_config = self.get_ingress_config()
        self.allocator = SubPathAllocator(self.application.code, self.ingress_config.port_map)

    def get_ingress_config(self) -> IngressConfig:
        """Get ingress config from cluster info"""
        cluster = EnvClusterService(self.env).get_cluster()
        return cluster.ingress_config

    def get_shortest(self) -> Optional[Subpath]:
        """Get the shortest subpath object"""
        subpaths = self.all()
        if not subpaths:
            return None
        return sorted(subpaths, key=Subpath.sort_by_len)[0]

    def all(self) -> List[Subpath]:
        """Get all assigned subpaths for current env"""
        sub_path_domains = self.ingress_config.sub_path_domains
        if not sub_path_domains:
            return []

        items = self.allocator.list_available(
            sub_path_domains, self.env.module.name, self.env.environment, self.env.module.is_default
        )

        # Add legacy subpaths if configured
        if settings.USE_LEGACY_SUB_PATH_PATTERN:
            legacy_path = get_legacy_compatible_path(self.env)
            items.extend([self.allocator.make_stable_obj(c, legacy_path) for c in sub_path_domains])
            # Sort items because legacy subpath obj has low priority type
            items.sort(key=Subpath.sort_by_type)
        return items

    def get_highest_priority(self) -> Optional[Subpath]:
        sub_path_domains = self.ingress_config.sub_path_domains
        if not sub_path_domains:
            return None
        return self.allocator.get_highest_priority(
            sorted(sub_path_domains, key=attrgetter("reserved"))[0],
            self.env.module.name,
            self.env.environment,
            self.env.module.is_default,
        )


def get_legacy_compatible_path(env: ModuleEnvironment) -> str:
    """Get the subpath for environment which is compatible with legacy infrastructure.
    This path is unique among all EngineApps.
    See LegacyAppIngressMgr in Workload service for more details.
    """
    name = env.engine_app.name
    return f'/{env.module.region}-{name}/'


class SubPathAllocator:
    """Allocate subpath objects

    :param port_map: The PortMap config
    """

    # Reserved word of application code, safe for concatenating address
    sep = '--'

    def __init__(self, app_code: str, port_map: PortMap):
        self.app_code = app_code
        self.port_map = port_map

    def list_available(
        self, domain_cfgs: List[DomainCfg], module_name: str, env_name: str, is_default: bool
    ) -> List[Subpath]:
        """Get all available subpath objects, the result was sorted by type,
        see `SubpathPriorityType` for more details

        :param domain_cfgs: A list of domain configs
        :param module: Name of module
        :param env_name: Name of environment, "stag" or "prod"
        :param is_default: Whether current module is "default" module
        """
        subpaths = [self.for_universal(c, module_name, env_name) for c in domain_cfgs]
        if is_default:
            subpaths.extend([self.for_default_module(c, env_name) for c in domain_cfgs])
            if env_name == AppEnvName.PROD.value:
                subpaths.extend([self.for_default_module_prod_env(c) for c in domain_cfgs])
        return subpaths

    def get_highest_priority(
        self, domain_cfg: DomainCfg, module_name: str, env_name: str, is_default: bool
    ) -> Subpath:
        """Get the subpath object for given environment, it will return the object
        with the highest priority, see `SubpathPriorityType` for more details.
        """
        subpaths = self.list_available([domain_cfg], module_name, env_name, is_default)
        return subpaths[-1]

    def for_universal(self, domain_cfg: DomainCfg, module_name: str, env_name: str) -> Subpath:
        """Return subpath object whose value depends on app_code, module and
        environment name, suitable for all environments.
        """
        return self.make_stable_obj(domain_cfg, self._make_subpath(env_name, module_name, self.app_code))

    def for_default_module(self, domain_cfg: DomainCfg, env_name: str) -> Subpath:
        """Return subpath object whose value depends on app_code and environment name,
        always bound to default module.
        """
        return Subpath(
            subpath=self._make_subpath(env_name, self.app_code),
            host=domain_cfg.name,
            type=SubpathPriorityType.WITHOUT_MODULE,
            https_enabled=domain_cfg.https_enabled,
            port_map=self.port_map,
        )

    def for_default_module_prod_env(self, domain_cfg: DomainCfg) -> Subpath:
        """Return subpath object whose value depends on app_code only, always bound
        to the default module's prod environment.
        """
        return Subpath(
            subpath=self._make_subpath(self.app_code),
            host=domain_cfg.name,
            type=SubpathPriorityType.ONLY_CODE,
            https_enabled=domain_cfg.https_enabled,
            port_map=self.port_map,
        )

    def make_stable_obj(self, domain_cfg: DomainCfg, subpath: str) -> Subpath:
        """Make a subpath object with "STABLE" type."""
        return Subpath(
            subpath=subpath,
            host=domain_cfg.name,
            type=SubpathPriorityType.STABLE,
            https_enabled=domain_cfg.https_enabled,
            port_map=self.port_map,
        )

    @classmethod
    def _make_subpath(cls, *parts: str) -> str:
        """Make a subpath"""
        safe_parts = [to_dns_safe(p) for p in parts]
        return '/{}/'.format(cls.sep.join(safe_parts).lower())
