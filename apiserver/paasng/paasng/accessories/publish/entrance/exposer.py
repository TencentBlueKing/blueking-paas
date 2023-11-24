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
"""Manage logics related with how to expose an application"""
import logging
from typing import Dict, Optional

from paas_wl.core.env import env_is_running
from paas_wl.workloads.networking.entrance.addrs import EnvExposedURL
from paas_wl.workloads.networking.entrance.handlers import refresh_module_domains
from paas_wl.workloads.networking.entrance.shim import get_builtin_addr_preferred
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def env_is_deployed(env: ModuleEnvironment) -> bool:
    """Return the deployed status(aka "is_running") of an environment object"""
    return env_is_running(env)


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


def get_exposed_links(application: Application) -> Dict:
    """Return exposed links for default module"""
    return get_module_exposed_links(application.get_default_module())


def get_exposed_url(module_env: ModuleEnvironment) -> Optional[EnvExposedURL]:
    """Get exposed url object of given environment, if the environment is not
    running, return None instead.

    - Custom domain is not included
    - Both cloud-native and default application are supported

    :returns: Return the shortest url by default. If a preferred root domain was
        set and a match can be found using that domain, the matched address will
        be returned in priority.
    """
    is_living, addr = get_builtin_addr_preferred(module_env)
    if not is_living or not addr:
        return None
    return addr.to_exposed_url()


# Exposed URL type related functions start
def update_exposed_url_type_to_subdomain(module: Module):
    """Update a module's exposed_url_type to subdomain"""
    # Return directly if exposed_url_type is already subdomain
    if module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        return

    module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
    module.save(update_fields=["exposed_url_type"])

    refresh_module_domains(module)

    # Also update app's address's in market if needed
    from paasng.accessories.publish.sync_market.handlers import sync_external_url_to_market

    sync_external_url_to_market(application=module.application)


# Exposed URL type related functions end
