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

from typing import Dict, List

from django.conf import settings

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvVarSource
from paas_wl.bk_app.dev_sandbox.entities import DevSandboxEnvVar
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.building import SlugbuilderInfo
from paasng.platform.engine.configurations.config_var import (
    EnvVarSource,
    UnifiedEnvVarsReader,
    list_vars_builtin_app_basic,
)
from paasng.platform.engine.deploy.bg_build.utils import get_envs_from_pypi_url
from paasng.platform.modules.models import Module


def generate_env_vars(module: Module) -> list[DevSandboxEnvVar]:
    envs = list_vars_builtin_app_basic(module.application).kv_map
    envs.update(
        {
            f"{settings.CONFIGVAR_SYSTEM_PREFIX}ENVIRONMENT": "dev",
            f"{settings.CONFIGVAR_SYSTEM_PREFIX}APP_LOG_PATH": settings.MUL_MODULE_VOLUME_MOUNT_APP_LOGGING_DIR,
        }
    )

    # Inject pip index url
    if settings.PYTHON_BUILDPACK_PIP_INDEX_URL:
        envs.update(get_envs_from_pypi_url(settings.PYTHON_BUILDPACK_PIP_INDEX_URL))

    # Inject build config by app module
    build_info = SlugbuilderInfo.from_module(module)
    envs.update(build_info.environments)
    if buildpacks := build_info.buildpacks_info:
        envs["REQUIRED_BUILDPACKS"] = _buildpacks_as_build_env(buildpacks)

    # Inject dev server config
    envs["DEV_SERVER_ADDR"] = f":{settings.DEV_SANDBOX_DEVSERVER_PORT}"
    envs["CORS_ALLOW_ORIGINS"] = settings.DEV_SANDBOX_CORS_ALLOW_ORIGINS

    result = [
        DevSandboxEnvVar(key=key, value=value, source=DevSandboxEnvVarSource.STAG) for key, value in envs.items()
    ]
    return result


def _buildpacks_as_build_env(buildpacks: List[Dict]) -> str:
    """buildpacks to REQUIRED_BUILDPACKS env

    note: copy from BuildProcess.buildpacks_as_build_env
    """
    if not buildpacks:
        return ""

    required_buildpacks = []
    for i in buildpacks:
        buildpack = []
        for key in ("type", "name", "url", "version"):
            buildpack.append(i.get(key) or '""')

        required_buildpacks.append(" ".join(buildpack))

    return ";".join(required_buildpacks)


def get_env_vars_selected_addons(
    env: ModuleEnvironment, selected_addons_service_names: List[str] | None
) -> List[DevSandboxEnvVar]:
    """Get environment variables including selected addon services.

    :param env: The module environment to read from.
    :param selected_addons_service_names: list of selected addons service.
    """
    _base_vars = UnifiedEnvVarsReader(env).get_kv_map(exclude_sources=[EnvVarSource.BUILTIN_ADDONS])
    base_vars = [
        DevSandboxEnvVar(
            key=key,
            value=value,
            source=DevSandboxEnvVarSource.STAG,
        )
        for key, value in _base_vars.items()
    ]

    addon_vars = list_vars_builtin_addons_custom(env, selected_addons_service_names)

    # 如果有相同的 key, addon_vars 因为后遍历到， 所以会覆盖 base_vars 中的值
    result = {item.key: item for item in (base_vars + addon_vars)}
    return list(result.values())


def list_vars_builtin_addons_custom(
    env: ModuleEnvironment, selected_addons_service_names: List[str] | None
) -> List[DevSandboxEnvVar]:
    """Retrieve environment variables for specified addon services.

    :param env: The module environment to read from.
    :param selected_addons_service_names: list of selected addons service.
    """
    var_groups = ServiceSharingManager(env.module).get_env_variable_groups(
        env, filter_enabled=True
    ) + mixed_service_mgr.get_env_var_groups(env.get_engine_app(), filter_enabled=True)

    if selected_addons_service_names is not None:
        var_groups = [group for group in var_groups if group.service.name in selected_addons_service_names]

    sensitive_fields = {
        field
        for group in var_groups
        for field in (group.should_hidden_fields or []) + (group.should_remove_fields or [])
    }

    return [
        DevSandboxEnvVar(
            key=key,
            value=value,
            source=DevSandboxEnvVarSource.STAG,
            sensitive=key in sensitive_fields,
        )
        for group in var_groups
        for key, value in group.data.items()
    ]
