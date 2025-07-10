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
"""Listers contains all the lister functions for list env variables."""

from typing import Iterator

from django.conf import settings

from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.models import get_svc_disc_as_env_variables
from paasng.platform.engine.configurations.env_var.entities import EnvVariableList, EnvVariableObj
from paasng.platform.engine.configurations.ingress import AppDefaultDomains, AppDefaultSubpaths
from paasng.platform.engine.configurations.provider import env_vars_providers
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import (
    ENVIRONMENT_ID_FOR_GLOBAL,
    ConfigVar,
)
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.utils.blobstore import make_blob_store_env

# Below list_vars_{} functions are used to list environment variables for a given source,
# it works as a part of the `UnifiedEnvVarsReader` class but can also be used independently.


def list_vars_user_preset(env: ModuleEnvironment) -> EnvVariableList:
    """list the env variables configured("preset") by the application's desc file."""
    qs: Iterator[PresetEnvVariable] = PresetEnvVariable.objects.filter(module=env.module)
    return EnvVariableList(
        EnvVariableObj(key=item.key, value=item.value, description="user preset")
        for item in qs
        if item.is_within_scope(ConfigVarEnvName(env.environment))
    )


def list_vars_user_configured(env: ModuleEnvironment) -> EnvVariableList:
    """List the env variables configured by the user."""
    config_vars = ConfigVar.objects.filter(
        module=env.module, environment_id__in=(ENVIRONMENT_ID_FOR_GLOBAL, env.id)
    ).order_by("environment_id")
    return EnvVariableList(
        EnvVariableObj(key=item.key, value=item.value, description="user configured") for item in config_vars
    )


def list_vars_builtin_blobstore(env: ModuleEnvironment) -> EnvVariableList:
    """List the env variables related to blobstore."""
    m = ModuleRuntimeManager(env.module)
    if not m.is_need_blobstore_env:
        return EnvVariableList()
    kv_map = make_blob_store_env(encrypt=m.is_secure_encrypted_runtime)
    return EnvVariableList(
        EnvVariableObj(key=key, value=value, description="blobstore") for key, value in kv_map.items()
    )


def list_vars_builtin_svc_disc(env: ModuleEnvironment) -> EnvVariableList:
    """List the env variables related to service discovery."""
    svc_disc_vars = get_svc_disc_as_env_variables(env)
    return EnvVariableList(
        EnvVariableObj(key=key, value=value, description="service discovery") for key, value in svc_disc_vars.items()
    )


def list_vars_builtin_addons(env: ModuleEnvironment) -> EnvVariableList:
    """List the env variables provided by addons."""
    # Load both bound and shared services
    var_groups = ServiceSharingManager(env.module).get_env_variable_groups(
        env, filter_enabled=True
    ) + mixed_service_mgr.get_env_var_groups(env.get_engine_app(), filter_enabled=True)

    var_map = {}
    for group in var_groups:
        for key, value in group.data.items():
            var_map[key] = EnvVariableObj(
                key=key,
                value=value,
                description=str(group.service.display_name),
            )
    return EnvVariableList(var_map.values())


def list_vars_builtin_default_entrance(env: ModuleEnvironment) -> EnvVariableList:
    """List the env variables related with the default entrance."""
    entrance_vars = {
        **AppDefaultDomains(env).as_env_vars(),
        **AppDefaultSubpaths(env).as_env_vars(),
    }
    return EnvVariableList(
        EnvVariableObj(key=key, value=value, description="default entrance") for key, value in entrance_vars.items()
    )


def list_vars_builtin_misc(env: ModuleEnvironment) -> EnvVariableList:
    """List the miscellaneous built-in env variables."""
    from paasng.platform.engine.configurations.config_var import (
        generate_wl_builtin_env_vars,
        get_builtin_env_variables,
    )

    result = EnvVariableList()
    # Part: Gather values from registered env variables providers
    result.extend(
        EnvVariableObj(key=key, value=value, description="misc built-in")
        for key, value in env_vars_providers.gather(env).items()
    )
    # TODO: Refactor get_builtin_env_variables to return EnvVariableObj instances directly
    # to preserve the description field.
    result.extend(
        EnvVariableObj(key=key, value=value, description="misc built-in")
        for key, value in get_builtin_env_variables(env.get_engine_app(), settings.CONFIGVAR_SYSTEM_PREFIX).items()
    )

    # Port: workloads related env vars
    result.extend(
        EnvVariableObj(key=item.key, value=item.value, description=item.description)
        for item in generate_wl_builtin_env_vars(settings.CONFIGVAR_SYSTEM_PREFIX, env)
    )
    return result
