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
from typing import List

from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.engine.models.managers import ConfigVarManager
from paasng.platform.modules.models import Module

from .entities import ImportEnvVarsResult


def import_env_vars(
    module: Module, env_vars: List[EnvVar], overlay_env_vars: List[EnvVarOverlay]
) -> ImportEnvVarsResult:
    """Import environment variables, existing data that is not in the input list may be removed.

    :param env_vars: The default variables.
    :param overlay_env_vars: The environment-specified variables.
    :return: A result object.
    """
    config_vars: List[ConfigVar] = []
    for var in env_vars:
        config_vars.append(
            ConfigVar(
                is_global=True,
                environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
                module=module,
                key=var.name,
                value=var.value,
            )
        )
    for overlay_var in overlay_env_vars:
        env = module.envs.get(environment=overlay_var.envName)
        config_vars.append(
            ConfigVar(
                is_global=False,
                environment_id=env.pk,
                module=module,
                key=overlay_var.name,
                value=overlay_var.value,
            )
        )

    # Load config vars to database
    var_mgr = ConfigVarManager()
    ret = var_mgr.apply_vars_to_module(module, config_vars)

    # Remove other variables
    keys = [var.key for var in config_vars]
    removed_num = var_mgr.remove_bulk(module, exclude_keys=keys)
    return ImportEnvVarsResult(affected_num=(ret.create_num + ret.overwrited_num), removed_num=removed_num)
