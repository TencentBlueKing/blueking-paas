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

from typing import List

from paasng.platform.bkapp_model.entities import EnvVar, EnvVarOverlay
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.models import Module
from paasng.utils.structure import NotSetType

from .result import CommonSyncResult


def sync_env_vars(
    module: Module, env_vars: List[EnvVar], overlay_env_vars: List[EnvVarOverlay] | NotSetType
) -> CommonSyncResult:
    """Sync environment variables to db model, existing data that is not in the input
    list might be removed.

    **This function writes data to PresetEnvVariable model.**

    :param module: app module
    :param env_vars: The default variables
    :param overlay_env_vars: The environment-specified variables
    :return: sync result
    """
    ret = CommonSyncResult()
    if isinstance(overlay_env_vars, NotSetType):
        overlay_env_vars = []

    # Build the index of existing data first to remove data later.
    # Data structure: {(env_name, key): pk}
    existing_index: dict[tuple[str, str], int] = {}
    for var_obj in PresetEnvVariable.objects.filter(module=module):
        existing_index[(var_obj.environment_name, var_obj.key)] = var_obj.pk

    # Upsert the input data
    for var in env_vars:
        env_name = ConfigVarEnvName.GLOBAL
        _, created = PresetEnvVariable.objects.update_or_create(
            module=module,
            environment_name=env_name.value,
            key=var.name,
            defaults={"value": var.value, "description": var.description, "tenant_id": module.tenant_id},
        )
        ret.incr_by_created_flag(created)
        existing_index.pop((env_name.value, var.name), None)

    for overlay_var in overlay_env_vars:
        env_name = ConfigVarEnvName(overlay_var.env_name)
        _, created = PresetEnvVariable.objects.update_or_create(
            module=module,
            environment_name=env_name.value,
            key=overlay_var.name,
            defaults={
                "value": overlay_var.value,
                "description": overlay_var.description,
                "tenant_id": module.tenant_id,
            },
        )
        ret.incr_by_created_flag(created)
        existing_index.pop((env_name.value, overlay_var.name), None)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = PresetEnvVariable.objects.filter(module=module, id__in=existing_index.values()).delete()
    return ret
