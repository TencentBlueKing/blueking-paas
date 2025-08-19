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


def generate_replica_overrides(m: Module, process_names: list[str]) -> dict[str | tuple[str, str], int | NotSetType]:
    """生成副本字段的覆盖值. 该值覆盖 bkapp entity 中的副本字段后, 通过 entities_syncer 同步到 bkapp model 时, 副本数会以页面数据为准

    示例: 假设 app_desc 中 web 进程的副本数为 2, 而页面的副本数已经扩容成了 5, 则此函数返回 {web: NOTSET}.
      此时设置 app_desc 中的 web 进程副本数为 NOTSET, 最终同步到 bkapp model 时, 不会更新副本值, 因此还是页面配置的副本数 5

    :param m: 应用模块
    :param process_names: 目标进程名列表
    :return: 副本字段的覆盖值. 格式如 {web: 1, (web, prod): 2}
    """
    replicas_values = {}

    proc_specs = ModuleProcessSpec.objects.filter(module=m, name__in=process_names)
    for proc in proc_specs:
        manager_name = fieldmgr.FieldManager(m, fieldmgr.f_proc_replicas(proc.name)).get()
        if manager_name == fieldmgr.FieldMgrName.APP_DESC:
            replicas_values[proc.name] = proc.target_replicas
        elif manager_name == fieldmgr.FieldMgrName.WEB_FORM:
            replicas_values[proc.name] = NOTSET

        for env_name in AppEnvName:
            try:
                env_overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=proc, environment_name=env_name)
            except ProcessSpecEnvOverlay.DoesNotExist:
                replicas_values[(proc.name, env_name)] = NOTSET
                continue

            manager_name = fieldmgr.FieldManager(m, fieldmgr.f_overlay_replicas(proc.name, env_name)).get()
            if manager_name == fieldmgr.FieldMgrName.APP_DESC and env_overlay.target_replicas:
                replicas_values[(proc.name, env_name)] = env_overlay.target_replicas
            elif manager_name == fieldmgr.FieldMgrName.WEB_FORM:
                replicas_values[(proc.name, env_name)] = NOTSET

    return replicas_values
