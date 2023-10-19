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
import copy
from typing import TYPE_CHECKING, List

from blue_krill.data_types.enum import StructuredEnum
from django.conf import settings

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, EnvVar
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.config_var import get_builtin_env_variables
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar, get_config_vars

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


def generate_user_configurations(env: ModuleEnvironment) -> List[EnvVar]:
    """获取用户定义的环境变量配置"""
    return [
        EnvVar(name=name.upper(), value=value) for name, value in get_config_vars(env.module, env.environment).items()
    ]


def generate_builtin_configurations(env: ModuleEnvironment) -> List[EnvVar]:

    return [EnvVar(name="PORT", value=str(settings.CONTAINER_PORT))] + [
        EnvVar(name=name.upper(), value=value)
        for name, value in get_builtin_env_variables(env.engine_app, settings.CONFIGVAR_SYSTEM_PREFIX).items()
    ]


class MergeStrategy(str, StructuredEnum):
    OVERRIDE = "Override"
    IGNORE = "Ignore"


def merge_envvars(x: List[EnvVar], y: List[EnvVar], strategy: MergeStrategy = MergeStrategy.OVERRIDE):
    """merge envvars x and y, if key conflict, will resolve with given strategy.

    MergeStrategy.OVERRIDE: will use the one in y if x and y have same name EnvVar
    MergeStrategy.IGNORE: will ignore the EnvVar in y if x and y have same name EnvVar
    """
    merged = copy.deepcopy(x)
    y_vars = {var.name: var.value for var in y}
    for var in merged:
        if var.name in y_vars:
            value = y_vars.pop(var.name)
            if strategy == MergeStrategy.OVERRIDE:
                var.value = value
    for name, value in y_vars.items():
        merged.append(EnvVar(name=name, value=value))
    return merged


class EnvVarsReader:
    """Read "configurations.env" from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self, module: 'Module') -> List[ConfigVar]:
        """Read all the env vars and keep the original formatting

        :param module: App module object
        :retrun: A list contains all env vars defined at `configuration.env` and  `envOverlay.envVariables`
        """
        config_vars = []

        # env vars that take effect in all environments
        for env in self.res.spec.configuration.env:
            config_vars.append(
                ConfigVar(
                    module=module,
                    is_global=True,
                    environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
                    key=env.name,
                    value=env.value,
                    description="auto created from BkApp",
                )
            )

        # env vars that take effect in the specify environment
        if self.res.spec.envOverlay and self.res.spec.envOverlay.envVariables:
            for env_overlay in self.res.spec.envOverlay.envVariables:
                module_env = module.get_envs(env_overlay.envName)
                config_vars.append(
                    ConfigVar(
                        module=module,
                        environment=module_env,
                        key=env_overlay.name,
                        value=env_overlay.value,
                        description="auto created from BkApp",
                    )
                )
        return config_vars
