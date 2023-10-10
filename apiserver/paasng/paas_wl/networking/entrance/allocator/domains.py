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
"""Domain management"""
from dataclasses import dataclass, field
from operator import attrgetter
from typing import Dict, List, Optional

from blue_krill.data_types.enum import EnumField, StructuredEnum

from paas_wl.cluster.models import Domain as DomainCfg
from paas_wl.cluster.models import IngressConfig, PortMap
from paas_wl.cluster.shim import EnvClusterService
from paas_wl.networking.entrance.addrs import URL
from paas_wl.networking.entrance.utils import to_dns_safe
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.applications.models import ModuleEnvironment


class DomainPriorityType(int, StructuredEnum):
    STABLE = EnumField(1, label="无缩写，完整域名")
    WITHOUT_MODULE = EnumField(2, label="无模块，指向主模块")
    ONLY_CODE = EnumField(3, label="无模块无环境，指向主模块生产环境")


@dataclass
class Domain:
    """A domain object"""

    host: str
    https_enabled: bool = False
    https_rewrite: bool = False
    type: int = DomainPriorityType.STABLE
    port_map: PortMap = field(default_factory=PortMap)

    def as_url(self) -> URL:
        protocol = "https" if self.https_enabled else "http"
        port = self.port_map.get_port_num(protocol)
        return URL(
            protocol=protocol,
            hostname=self.host,
            port=port,
            path="",
        )

    def as_dict(self) -> Dict:
        return {'host': self.host, 'https_enabled': self.https_enabled}

    @staticmethod
    def sort_by_len(domain: 'Domain'):
        return len(domain.host)

    @staticmethod
    def sort_by_type(domain: 'Domain'):
        return domain.type


class ModuleEnvDomains:
    """managing domains for module environment"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.application = env.module.application
        self.ingress_config = self.get_ingress_config()
        self.allocator = SubDomainAllocator(self.application.code, self.ingress_config.port_map)

    def get_ingress_config(self) -> IngressConfig:
        """Get ingress config from cluster info"""
        cluster = EnvClusterService(self.env).get_cluster()
        return cluster.ingress_config

    def all(self) -> List[Domain]:
        """Get all assigned domains for current env"""
        root_domains = self.ingress_config.app_root_domains
        if not root_domains:
            return []

        return self.allocator.list_available(
            root_domains, self.env.module.name, self.env.environment, self.env.module.is_default
        )

    def get_highest_priority(self) -> Optional[Domain]:
        root_domains = self.ingress_config.app_root_domains
        if not root_domains:
            return None

        return self.allocator.get_highest_priority(
            sorted(root_domains, key=attrgetter("reserved"))[0],
            self.env.module.name,
            self.env.environment,
            self.env.module.is_default,
        )


class SubDomainAllocator:
    """Allocate domain objects

    :param port_map: The PortMap config
    """

    DOT_SEP = '-dot-'

    def __init__(self, app_code: str, port_map: PortMap):
        self.app_code = app_code
        self.port_map = port_map

    def list_available(
        self, domain_cfgs: List[DomainCfg], module_name: str, env_name: str, is_default: bool
    ) -> List[Domain]:
        """Get all available domain objects, the result was sorted by `DomainPriorityType`

        :param domain_cfgs: A list of domain configs, usually defined in ingress config
        :param module: Name of module
        :param env_name: Name of environment, "stag" or "prod"
        :param is_default: Whether current module is "default" module
        """
        domains = [self.for_universal(c, module_name, env_name) for c in domain_cfgs]
        if is_default:
            domains.extend([self.for_default_module(c, env_name) for c in domain_cfgs])
            if env_name == AppEnvName.PROD.value:
                domains.extend([self.for_default_module_prod_env(c) for c in domain_cfgs])
        return domains

    def get_highest_priority(self, domain_cfg: DomainCfg, module_name: str, env_name: str, is_default: bool) -> Domain:
        """Get the Domain object for given environment, it will return the object
        with the highest priority, see `DomainPriorityType` for more details.
        """
        domains = self.list_available([domain_cfg], module_name, env_name, is_default)
        return domains[-1]

    def for_universal(self, domain_cfg: DomainCfg, module_name: str, env_name: str) -> Domain:
        """Return a Domain object whose host depends on app_code, module and
        environment name, suitable for all environments.
        """
        return Domain(
            host=self._make_host(domain_cfg.name, env_name, module_name, self.app_code),
            type=DomainPriorityType.STABLE,
            https_enabled=domain_cfg.https_enabled,
            port_map=self.port_map,
        )

    def for_default_module(self, domain_cfg: DomainCfg, env_name: str) -> Domain:
        """Return a Domain object whose host depends on app_code and environment name,
        always bound to default module.
        """
        return Domain(
            host=self._make_host(domain_cfg.name, env_name, self.app_code),
            type=DomainPriorityType.WITHOUT_MODULE,
            https_enabled=domain_cfg.https_enabled,
            port_map=self.port_map,
        )

    def for_default_module_prod_env(self, domain_cfg: DomainCfg) -> Domain:
        """Return a Domain object whose host depends on app_code only, always bound
        to the default module's prod environment.
        """
        return Domain(
            host=self._make_host(domain_cfg.name, self.app_code),
            type=DomainPriorityType.ONLY_CODE,
            https_enabled=domain_cfg.https_enabled,
            port_map=self.port_map,
        )

    @classmethod
    def _make_host(cls, root_domain: str, *parts: str):
        """Make a host name"""
        safe_parts = [to_dns_safe(s) for s in parts]
        return (cls.DOT_SEP.join(safe_parts) + '.' + root_domain).lower()
