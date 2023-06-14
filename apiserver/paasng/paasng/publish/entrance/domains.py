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
from typing import List, NamedTuple, Optional

from paas_wl.cluster.models import IngressConfig
from paas_wl.cluster.shim import EnvClusterService
from paas_wl.networking.entrance.allocator.domains import Domain, SubDomainAllocator
from paasng.engine.constants import AppEnvName
from paasng.platform.applications.models import ModuleEnvironment


class PreDomains(NamedTuple):
    """Preallocated domains, include both environments"""

    stag: Domain
    prod: Domain


def get_preallocated_domains_by_env(env: ModuleEnvironment) -> List[Domain]:
    """Get all pre-allocated domains for a environment which may has not been
    deployed yet. Results length is equal to length of configured root domains.
    """
    app = env.application
    module = env.module
    cluster = EnvClusterService(env).get_cluster()
    ingress_config = cluster.ingress_config

    # Iterate configured root domains, get domains
    allocator = SubDomainAllocator(app.code, ingress_config.port_map)
    results: List[Domain] = []
    for domain_cfg in ingress_config.app_root_domains:
        if not env.module.is_default:
            results.append(allocator.for_universal(domain_cfg, module.name, env.environment))
        else:
            if env.environment == AppEnvName.STAG.value:
                results.append(allocator.for_default_module(domain_cfg, 'stag'))
            else:
                results.append(allocator.for_default_module_prod_env(domain_cfg))
    return results


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

    allocator = SubDomainAllocator(app_code, ingress_config.port_map)
    domain_cfg = ingress_config.default_root_domain
    if not module_name:
        return PreDomains(
            stag=allocator.for_default_module(domain_cfg, 'stag'),
            prod=allocator.for_default_module_prod_env(domain_cfg),
        )
    else:
        return PreDomains(
            stag=allocator.for_universal(domain_cfg, module_name, 'stag'),
            prod=allocator.for_universal(domain_cfg, module_name, 'prod'),
        )
