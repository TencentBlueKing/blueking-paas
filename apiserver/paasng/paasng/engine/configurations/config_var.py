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
"""Config variables related functions"""
from typing import Dict, Optional

from django.conf import settings

from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.dev_resources.servicehub.sharing import ServiceSharingManager
from paasng.engine.models import Deployment
from paasng.engine.models.config_var import generate_blobstore_env_vars, generate_builtin_env_vars, get_config_vars
from paasng.engine.networking import AppDefaultDomains, AppDefaultSubpaths
from paasng.platform.applications.models import ModuleEnvironment
from paasng.publish.entrance.exposer import get_bk_doc_url_prefix

from .provider import env_vars_providers


def get_env_variables(
    env: ModuleEnvironment, include_builtin=True, deployment: Optional[Deployment] = None
) -> Dict[str, str]:
    """Get env vars for current environment, this will includes:

    - env vars from services
    - user defined config vars
    - built-in env vars
    - (optional) vars defined by deployment description file

    :param include_builtin: Whether include builtin config vars
    :param deployment: Optional deployment object to get vars defined in description file
    :returns: Dict of env vars
    """
    result = {}
    engine_app = env.get_engine_app()

    # Part: Gather values from registered env variables providers, it has lowest priority
    result.update(env_vars_providers.gather(env, deployment))

    # Part: system-wide env vars
    if include_builtin:
        result.update(generate_builtin_env_vars(engine_app, settings.CONFIGVAR_SYSTEM_PREFIX))

    # Part: Address for bk_docs_center saas
    # Q: Why not in the generate_builtin_env_vars method？

    # method(get_preallocated_address) and module(ConfigVar) will be referenced circularly
    result.update({'BK_DOCS_URL_PREFIX': get_bk_doc_url_prefix()})

    # Part: insert blobstore env vars
    result.update(generate_blobstore_env_vars(engine_app))

    # Part: user defined env vars
    # Q: Why don't we using engine_app directly to get ConfigVars?
    #
    # Because Config Vars, unlike ServiceInstance, is not bind to EngineApp. It
    # has application global type which shares under every engine_app/environment of an
    # application.
    result.update(get_config_vars(engine_app.env.module, engine_app.env.environment))

    # Part: env vars shared from other modules
    result.update(ServiceSharingManager(env.module).get_env_variables(env))

    # Part: env vars provided by services
    result.update(mixed_service_mgr.get_env_vars(engine_app))

    # Part: Application's default sub domains/paths
    result.update(AppDefaultDomains(env).as_env_vars())
    result.update(AppDefaultSubpaths(env).as_env_vars())
    return result
