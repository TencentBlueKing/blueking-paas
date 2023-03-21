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

from paas_wl.cnative.specs.v1alpha1.bk_app import EnvVar
from paasng.engine.configurations.config_var import get_builtin_env_variables
from paasng.platform.applications.models import ModuleEnvironment


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
