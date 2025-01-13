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

"""Subpaths management"""

from typing import List, NamedTuple, Optional

from paas_wl.infras.cluster.entities import IngressConfig
from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.networking.entrance.allocator.subpaths import Subpath, SubPathAllocator
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName


class PreSubpaths(NamedTuple):
    """Preallocated subpaths, include both environments"""

    stag: Subpath
    prod: Subpath


def get_preallocated_paths_by_env(env: ModuleEnvironment) -> List[Subpath]:
    """Get all pre-allocated subpaths for a environment which may has not been
    deployed yet. Results length is equal to length of configured subpath domains.
    """
    app = env.application
    module = env.module
    cluster = EnvClusterService(env).get_cluster()
    ingress_config = cluster.ingress_config

    # Iterate configured subpath domains, get subpaths
    allocator = SubPathAllocator(app.code, ingress_config.port_map)
    results: List[Subpath] = []
    for domain_cfg in ingress_config.sub_path_domains:
        if not env.module.is_default:
            results.append(allocator.for_universal(domain_cfg, module.name, env.environment))
        elif env.environment == AppEnvName.STAG.value:
            results.append(allocator.for_default_module(domain_cfg, "stag"))
        else:
            results.append(allocator.for_default_module_prod_env(domain_cfg))
    return results


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

    allocator = SubPathAllocator(app_code, ingress_config.port_map)
    domain_cfg = ingress_config.default_sub_path_domain
    if not module_name:
        # No module name was given, return shorten address which pointed to application's "default" module
        # automatically.
        return PreSubpaths(
            stag=allocator.for_default_module(domain_cfg, "stag"),
            prod=allocator.for_default_module_prod_env(domain_cfg),
        )
    else:
        # Generate address which always include module name
        return PreSubpaths(
            stag=allocator.for_universal(domain_cfg, module_name, "stag"),
            prod=allocator.for_universal(domain_cfg, module_name, "prod"),
        )


def get_legacy_compatible_path(env: ModuleEnvironment) -> str:
    """Get the subpath for environment which is compatible with legacy infrastructure.
    This path is unique among all EngineApps.
    See LegacyAppIngressMgr in Workload service for more details.
    """
    name = env.engine_app.name
    return f"/{env.module.region}-{name}/"
