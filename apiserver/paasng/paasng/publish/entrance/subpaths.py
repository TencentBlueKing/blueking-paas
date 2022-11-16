# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
"""Subpaths management"""
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.conf import settings

from paasng.engine.constants import AppEnvName
from paasng.engine.controller.cluster import get_engine_app_cluster
from paasng.engine.controller.models import IngressConfig, PortMap
from paasng.platform.applications.models import ModuleEnvironment
from paasng.publish.entrance.utils import URL, to_dns_safe


class SubpathPriorityType(int, StructuredEnum):
    STABLE = EnumField(1, label="无缩写")
    WITHOUT_MODULE = EnumField(2, label="无模块，指向主模块")
    ONLY_CODE = EnumField(3, label="无模块无环境，指向主模块生产环境")
    USER_PREFERRED = EnumField(4, label="用户指定的域名")


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


class PreSubpaths(NamedTuple):
    """Preallocated subpaths, include both environments"""

    stag: Subpath
    prod: Subpath


def get_preallocated_path(
    app_code: str, ingress_config: IngressConfig, module_name: Optional[str] = None
) -> Optional[PreSubpaths]:
    """Get the preallocated subpath for a application which was not released yet.

    if `module_name` was not given, the result will always use the main module.

    :param ingress_config: The ingress config dict
    :param module_name: Name of module, optional
    :returns: when cluster's sub-path was not configured, return None
    """
    if not ingress_config.sub_path_domains:
        return None

    safe_app_code = to_dns_safe(app_code)
    if not module_name:
        # No module name was given, return shorten address which pointed to application's "default" module
        # automatically.
        return PreSubpaths(
            stag=Subpath(
                subpath=ModuleEnvSubpaths.make_subpath('stag', safe_app_code),
                host=ingress_config.default_sub_path_domain.name,
                https_enabled=ingress_config.default_sub_path_domain.https_enabled,
                type=SubpathPriorityType.WITHOUT_MODULE,
                port_map=ingress_config.port_map,
            ),
            prod=Subpath(
                subpath=f'/{safe_app_code}/',
                host=ingress_config.default_sub_path_domain.name,
                https_enabled=ingress_config.default_sub_path_domain.https_enabled,
                type=SubpathPriorityType.ONLY_CODE,
                port_map=ingress_config.port_map,
            ),
        )
    else:
        # Generate address which always include module name
        safe_module_name = to_dns_safe(module_name)
        return PreSubpaths(
            stag=Subpath(
                subpath=ModuleEnvSubpaths.make_subpath('stag', safe_module_name, safe_app_code),
                host=ingress_config.default_sub_path_domain.name,
                https_enabled=ingress_config.default_sub_path_domain.https_enabled,
                type=SubpathPriorityType.STABLE,
                port_map=ingress_config.port_map,
            ),
            prod=Subpath(
                subpath=ModuleEnvSubpaths.make_subpath('prod', safe_module_name, safe_app_code),
                host=ingress_config.default_sub_path_domain.name,
                https_enabled=ingress_config.default_sub_path_domain.https_enabled,
                type=SubpathPriorityType.STABLE,
                port_map=ingress_config.port_map,
            ),
        )


class ModuleEnvSubpaths:
    """managing subpaths for module environment"""

    # Reserved word of application code, safe for concatenating address
    sep = '--'

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.application = env.module.application
        self.engine_app = env.engine_app

        self.part_env = to_dns_safe(env.environment)
        self.part_module = to_dns_safe(env.module.name)
        self.part_code = to_dns_safe(self.application.code)

        ingress_config = self.get_ingress_config()
        self.sub_path_domains = ingress_config.sub_path_domains
        self.port_map = ingress_config.port_map

    def get_ingress_config(self) -> IngressConfig:
        """Get ingress config from cluster info"""
        cluster = get_engine_app_cluster(self.application.region, self.engine_app.name)
        return cluster.ingress_config

    def get_shortest(self) -> Optional[Subpath]:
        """Get the shorted subpath object"""
        subpaths = self.all()
        if not subpaths:
            return None
        return sorted(subpaths, key=Subpath.sort_by_len)[0]

    def all(self) -> List[Subpath]:
        """Get all assigned subpaths for current env"""
        if not self.sub_path_domains:
            return []

        # TODO: Add legacy subpath
        subpaths = [*self.make_stable()]
        if self.env.module.is_default:
            subpaths.extend(self.make_without_module())

            # Assign a shortest domain for "prod" environment of "default" module
            if self.env.environment == AppEnvName.PROD:
                subpaths.extend(self.make_only_code())

        return subpaths

    def make_stable(self) -> List[Subpath]:
        """Make all stable subpath."""
        subpaths = [
            self.make_subpath(self.part_env, self.part_module, self.part_code),
        ]
        if settings.USE_LEGACY_SUB_PATH_PATTERN:
            subpaths.append(get_legacy_compatible_path(self.env))
        results = []
        for domain in self.sub_path_domains:
            for subpath in subpaths:
                results.append(
                    Subpath(
                        subpath=subpath,
                        host=domain.name,
                        type=SubpathPriorityType.STABLE,
                        https_enabled=domain.https_enabled,
                        port_map=self.port_map,
                    )
                )
        return results

    def make_without_module(self) -> List[Subpath]:
        """Make all subpath for default module."""
        return [
            Subpath(
                subpath=self.make_subpath(self.part_env, self.part_code),
                host=domain.name,
                type=SubpathPriorityType.WITHOUT_MODULE,
                https_enabled=domain.https_enabled,
                port_map=self.port_map,
            )
            for domain in self.sub_path_domains
        ]

    def make_only_code(self) -> List[Subpath]:
        """Make all subpath for default module prod env."""
        return [
            Subpath(
                subpath=self.make_subpath(self.part_code),
                host=domain.name,
                type=SubpathPriorityType.ONLY_CODE,
                https_enabled=domain.https_enabled,
                port_map=self.port_map,
            )
            for domain in self.sub_path_domains
        ]

    def make_user_preferred_one(self) -> Optional[Subpath]:
        """Make the subpath with user prefer root domain"""
        preferred = self.env.module.user_preferred_root_domain
        if not preferred:
            return None

        parts = [self.part_env, self.part_module, self.part_code]
        if self.env.module.is_default:
            parts = [self.part_env, self.part_code]
            if self.env.environment == "prod":
                parts = [self.part_code]
        return Subpath(
            subpath=self.make_subpath(*parts),
            host=preferred,
            type=SubpathPriorityType.USER_PREFERRED,
            https_enabled=any(domain.name == preferred and domain.https_enabled for domain in self.sub_path_domains),
            port_map=self.port_map,
        )

    @classmethod
    def make_subpath(cls, *parts):
        """Make a subpath"""
        return '/{}/'.format(cls.sep.join(parts).lower())


def get_legacy_compatible_path(env: ModuleEnvironment) -> str:
    """Get the subpath for environment which is compatible with legacy infrastructure.
    This path is unique among all EngineApps.
    See LegacyAppIngressMgr in Workload service for more details.
    """
    name = env.engine_app.name
    return f'/{env.module.region}-{name}/'
