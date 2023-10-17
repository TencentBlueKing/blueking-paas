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
from typing import List

from blue_krill.data_types.enum import StructuredEnum
from django.conf import settings

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, EnvVar
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.config_var import get_builtin_env_variables
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models.config_var import get_config_vars


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

    def read_all(self, env_name: AppEnvName) -> List[EnvVar]:
        """Read all env vars defined at given `env_name`

        :param env_name: Environment name
        :return: A list contains all env vars defined at given `env_name`, including `envOverlay`
        """
        env_vars = {}
        for env in self.res.spec.configuration.env:
            env_vars[env.name] = env.value

        if self.res.spec.envOverlay and self.res.spec.envOverlay.envVariables:
            for env_overlay in self.res.spec.envOverlay.envVariables:
                if env_overlay.envName == env_name:
                    env_vars[env_overlay.name] = env_overlay.value
        return [EnvVar(name=k, value=v) for k, v in env_vars.items()]
