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

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module
from paasng.utils.structure import NOTSET, NotSetType


def generate_locked_replicas_values(
    m: Module, process_names: list[str]
) -> dict[str | tuple[str, str], int | NotSetType]:
    """为应用模块生成副本字段锁定值. 依据此值替换 bkapp entity 的副本字段后, 通过 entities_syncer 同步时, 副本数不会发生变化

    :param m: 应用模块
    :param process_names: 需要锁定的进程名列表
    :return: 副本字段锁定值. 格式如 {web: 1, (web, prod): 2}
    """
    locked_values = {}

    proc_specs = ModuleProcessSpec.objects.filter(module=m, name__in=process_names)
    for proc in proc_specs:
        manager_name = fieldmgr.FieldManager(m, fieldmgr.f_proc_replicas(proc.name)).get()
        if manager_name == fieldmgr.FieldMgrName.APP_DESC:
            locked_values[proc.name] = proc.target_replicas
        elif manager_name == fieldmgr.FieldMgrName.WEB_FORM:
            locked_values[proc.name] = NOTSET

        for env_name in AppEnvName:
            try:
                env_overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=proc, environment_name=env_name)
            except ProcessSpecEnvOverlay.DoesNotExist:
                locked_values[(proc.name, env_name)] = NOTSET
                continue

            manager_name = fieldmgr.FieldManager(m, fieldmgr.f_overlay_replicas(proc.name, env_name)).get()
            if manager_name == fieldmgr.FieldMgrName.APP_DESC and env_overlay.target_replicas:
                locked_values[(proc.name, env_name)] = env_overlay.target_replicas
            elif manager_name == fieldmgr.FieldMgrName.WEB_FORM:
                locked_values[(proc.name, env_name)] = NOTSET

    return locked_values
