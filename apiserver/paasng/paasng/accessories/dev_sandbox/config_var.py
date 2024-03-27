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
from typing import Dict, List

from django.conf import settings
from django.utils.crypto import get_random_string

from paasng.platform.applications.models import Application
from paasng.platform.engine.configurations.building import SlugbuilderInfo
from paasng.platform.engine.configurations.config_var import generate_env_vars_for_app
from paasng.platform.engine.deploy.bg_build.utils import get_envs_from_pypi_url
from paasng.platform.modules.models import Module

CONTAINER_TOKEN_ENV = "TOKEN"


def generate_envs(app: Application, module: Module) -> Dict[str, str]:
    # TODO 补齐可能缺少的环境变量
    envs = generate_env_vars_for_app(app, settings.CONFIGVAR_SYSTEM_PREFIX)
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

    envs.update(_get_devserver_env())
    return envs


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


def _get_devserver_env() -> Dict[str, str]:
    """获取 devserver 的运行环境变量"""
    return {
        CONTAINER_TOKEN_ENV: get_random_string(length=8),
        "DEV_SERVER_ADDR": f":{settings.DEV_SANDBOX_DEVSERVER_PORT}",
    }
