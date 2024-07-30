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

import logging
from typing import Any, Dict, List

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess
from paasng.platform.bkapp_model.importer.entities import CommonImportResult
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def import_processes(module: Module, processes: List[BkAppProcess]) -> CommonImportResult:
    """Import processes data.

    :param processes: A list of BkAppProcess items.
    :return: The import result object.
    """
    ret = CommonImportResult()

    # Build the index of existing data first to remove data later.
    # Data structure: {process name: pk}
    existing_index = {}
    for proc_spec in ModuleProcessSpec.objects.filter(module=module):
        existing_index[proc_spec.name] = proc_spec.pk

    # Update or create data
    for process in processes:
        defaults: Dict[str, Any] = {
            "command": process.command,
            "args": process.args,
            "port": process.targetPort,
            "plan_name": process.resQuotaPlan or ResQuotaPlan.P_DEFAULT,
            # 为了兼容普通应用从 app_desc v2 升级到 app_desc v3, 导入时需要清空 proc_command 字段
            "proc_command": None,
        }

        # When the replicas value is None, only update the data if the process appears
        # for the first time in the module.
        if process.replicas is None:
            if not ModuleProcessSpec.objects.filter(module=module, name=process.name).exists():
                defaults["target_replicas"] = 1
        else:
            defaults["target_replicas"] = process.replicas

        if autoscaling := process.autoscaling:
            defaults["autoscaling"] = True
            defaults["scaling_config"] = {
                "min_replicas": autoscaling.minReplicas,
                "max_replicas": autoscaling.maxReplicas,
                "policy": autoscaling.policy,
            }
        if probes := process.probes:
            defaults["probes"] = probes.to_snake_case() if probes else None

        _, created = ModuleProcessSpec.objects.update_or_create(module=module, name=process.name, defaults=defaults)

        ret.incr_by_created_flag(created)
        # Move out from the index
        existing_index.pop(process.name, None)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ModuleProcessSpec.objects.filter(module=module, id__in=existing_index.values()).delete()
    return ret
