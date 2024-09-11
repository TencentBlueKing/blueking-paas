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

"""Utilities of PresetEnvVariable model, such as batch sync, etc."""

from typing import Dict, List, Tuple

from paasng.platform.bkapp_model.entities import EnvVar, EnvVarOverlay
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.models import Module


def batch_save(module: Module, env_vars: List[EnvVar], overlay_env_vars: List[EnvVarOverlay]):
    """Save environment variable lists to `PresetEnvVariable` model. The function do a
    fully sync so existing data that is not in the input list will be removed.

    :param module: app module
    :param env_vars: The default variables
    :param overlay_env_vars: The environment-specified variables
    """
    # Build the index of existing data first to remove data later.
    # Data structure: {(env_name, key): pk}
    existing_index: Dict[Tuple[str, str], int] = {}
    for var_obj in PresetEnvVariable.objects.filter(module=module):
        existing_index[(var_obj.environment_name, var_obj.key)] = var_obj.pk

    # Upsert the input data
    for var in env_vars:
        env_name = ConfigVarEnvName.GLOBAL
        PresetEnvVariable.objects.update_or_create(
            module=module, environment_name=env_name.value, key=var.name, defaults={"value": var.value}
        )
        existing_index.pop((env_name.value, var.name), None)
    for overlay_var in overlay_env_vars:
        env_name = ConfigVarEnvName(overlay_var.env_name)
        PresetEnvVariable.objects.update_or_create(
            module=module, environment_name=env_name.value, key=overlay_var.name, defaults={"value": overlay_var.value}
        )
        existing_index.pop((env_name.value, overlay_var.name), None)

    # Remove existing data that is not touched.
    PresetEnvVariable.objects.filter(module=module, id__in=existing_index.values()).delete()
