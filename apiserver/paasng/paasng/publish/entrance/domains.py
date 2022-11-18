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
from typing import Dict, List, NamedTuple, Optional

from blue_krill.data_types.enum import EnumField, StructuredEnum

from paasng.engine.controller.cluster import get_engine_app_cluster
from paasng.engine.controller.models import IngressConfig, PortMap
from paasng.platform.applications.models import ModuleEnvironment
from paasng.publish.entrance.utils import URL, to_dns_safe


class DomainPriorityType(int, StructuredEnum):
    STABLE = EnumField(1, label="无缩写，完整域名")
    WITHOUT_MODULE = EnumField(2, label="无模块，指向主模块")
    ONLY_CODE = EnumField(3, label="无模块无环境，指向主模块生产环境")
    USER_PREFERRED = EnumField(4, label="用户指定的域名")


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


class PreDomains(NamedTuple):
    """Preallocated domains, include both environments"""

    stag: Domain
    prod: Domain


def get_preallocated_domain(
    app_code: str, ingress_config: IngressConfig, module_name: Optional[str] = None
) -> Optional[PreDomains]:
    """Get the preallocated domain for a application which was not released yet.

    if `module_name` was not given, the result will always use the main module.

    :param ingress_config: The ingress config dict
    :param module_name: Name of module, optional
    :returns: when sub domain was not configured, return None
    """
    if not ingress_config.app_root_domains:
        return None

    safe_app_code = to_dns_safe(app_code)
    if not module_name:
        return PreDomains(
            stag=Domain(
                host=ModuleEnvDomains.make_host(ingress_config.default_root_domain.name, 'stag', safe_app_code),
                https_enabled=ingress_config.default_root_domain.https_enabled,
                type=DomainPriorityType.WITHOUT_MODULE,
                port_map=ingress_config.port_map,
            ),
            prod=Domain(
                host=ModuleEnvDomains.make_host(ingress_config.default_root_domain.name, safe_app_code),
                https_enabled=ingress_config.default_root_domain.https_enabled,
                type=DomainPriorityType.ONLY_CODE,
                port_map=ingress_config.port_map,
            ),
        )
    else:
        safe_module_name = to_dns_safe(module_name)
        return PreDomains(
            stag=Domain(
                host=ModuleEnvDomains.make_host(
                    ingress_config.default_root_domain.name, 'stag', safe_module_name, safe_app_code
                ),
                https_enabled=ingress_config.default_root_domain.https_enabled,
                type=DomainPriorityType.STABLE,
                port_map=ingress_config.port_map,
            ),
            prod=Domain(
                host=ModuleEnvDomains.make_host(
                    ingress_config.default_root_domain.name, 'prod', safe_module_name, safe_app_code
                ),
                https_enabled=ingress_config.default_root_domain.https_enabled,
                type=DomainPriorityType.STABLE,
                port_map=ingress_config.port_map,
            ),
        )


class ModuleEnvDomains:
    """managing domains for module environment"""

    DOT_SEP = '-dot-'

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.application = env.module.application
        self.engine_app = env.engine_app

        self.part_env = to_dns_safe(env.environment)
        self.part_module = to_dns_safe(env.module.name)
        self.part_code = to_dns_safe(self.application.code)

        ingress_config = self.get_ingress_config()
        self.root_domains = ingress_config.app_root_domains
        self.port_map = ingress_config.port_map

    def get_ingress_config(self) -> IngressConfig:
        """Get ingress config from cluster info"""
        cluster = get_engine_app_cluster(self.application.region, self.engine_app.name)
        return cluster.ingress_config

    def all(self) -> List[Domain]:
        """Get all assigned domains for current env"""
        if not self.root_domains:
            return []

        domains = [*self.make_stable()]
        if self.env.module.is_default:
            domains.extend(self.make_without_module())

            # Assign a shortest domain for "prod" environment of "default" module
            if self.env.environment == 'prod':
                domains.extend(self.make_only_code())

        return domains

    def make_stable(self) -> List[Domain]:
        """Make all stable domain."""
        return [
            Domain(
                host=self.make_host(domain.name, self.part_env, self.part_module, self.part_code),
                type=DomainPriorityType.STABLE,
                https_enabled=domain.https_enabled,
                port_map=self.port_map,
            )
            for domain in self.root_domains
        ]

    def make_without_module(self) -> List[Domain]:
        """Make all domain for default module."""
        return [
            Domain(
                host=self.make_host(domain.name, self.part_env, self.part_code),
                type=DomainPriorityType.WITHOUT_MODULE,
                https_enabled=domain.https_enabled,
                port_map=self.port_map,
            )
            for domain in self.root_domains
        ]

    def make_only_code(self) -> List[Domain]:
        """Make all domain for default module prod env."""
        return [
            Domain(
                host=self.make_host(domain.name, self.part_code),
                type=DomainPriorityType.ONLY_CODE,
                https_enabled=domain.https_enabled,
                port_map=self.port_map,
            )
            for domain in self.root_domains
        ]

    def make_user_preferred_one(self) -> Optional[Domain]:
        """Make the domain with user prefer root domain"""
        preferred = self.env.module.user_preferred_root_domain
        if not preferred:
            return None

        parts = [self.part_env, self.part_module, self.part_code]
        if self.env.module.is_default:
            parts = [self.part_env, self.part_code]
            if self.env.environment == "prod":
                parts = [self.part_code]
        return Domain(
            host=self.make_host(preferred, *parts),
            type=DomainPriorityType.USER_PREFERRED,
            https_enabled=any(domain.name == preferred and domain.https_enabled for domain in self.root_domains),
            port_map=self.port_map,
        )

    @classmethod
    def make_host(cls, root_domain: str, *parts):
        """Make a host name"""
        return (cls.DOT_SEP.join(parts) + '.' + root_domain).lower()
