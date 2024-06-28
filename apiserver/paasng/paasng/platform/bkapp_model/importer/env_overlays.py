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
from typing import Any, Callable, Dict, List, Type, cast

from paas_wl.bk_app.cnative.specs.crd.bk_app import AutoscalingOverlay, ReplicasOverlay, ResQuotaOverlay
from paasng.platform.bkapp_model.importer.entities import CommonImportResult
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def _upsert_replicas(proc_spec: ModuleProcessSpec, input_p: ReplicasOverlay) -> bool:
    """save ReplicasOverlay item"""
    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec, environment_name=input_p.envName, defaults={"target_replicas": input_p.count}
    )
    return created


def _upsert_res_quota(proc_spec: ModuleProcessSpec, input_p: ResQuotaOverlay) -> bool:
    """save ResQuotaOverlay item"""
    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec, environment_name=input_p.envName, defaults={"plan_name": input_p.plan}
    )
    return created


def _upsert_autoscaling(proc_spec: ModuleProcessSpec, input_p: AutoscalingOverlay) -> bool:
    """save AutoscalingOverlay item"""
    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec,
        environment_name=input_p.envName,
        defaults={
            "autoscaling": True,
            "scaling_config": {
                "min_replicas": input_p.minReplicas,
                "max_replicas": input_p.maxReplicas,
                "policy": input_p.policy,
            },
        },
    )
    return created


_handlers: Dict[Type, Callable[..., bool]] = {
    ReplicasOverlay: _upsert_replicas,
    ResQuotaOverlay: _upsert_res_quota,
    AutoscalingOverlay: _upsert_autoscaling,
}


def import_env_overlays(
    module: Module,
    overlay_replicas: List[ReplicasOverlay],
    overlay_res_quotas: List[ResQuotaOverlay],
    overlay_autoscalings: List[AutoscalingOverlay],
) -> CommonImportResult:
    """Import resQuota overlay data.

    :param overlay_replicas: A list of ResQuotaOverlay items.
    :param overlay_res_quotas: A list of ResQuotaOverlay items.
    :param overlay_autoscalings: A list of AutoscalingOverlay items.
    :return: The import result object.
    """
    ret = CommonImportResult()

    # Build the index of existing data first to remove data later.
    # Data structure: {(process name, environment name): pk}
    existing_index = {}
    existing_specs = {}
    for proc_spec in ModuleProcessSpec.objects.filter(module=module):
        existing_specs[proc_spec.name] = proc_spec
        for overlay_item in ProcessSpecEnvOverlay.objects.filter(proc_spec=proc_spec):
            existing_index[(proc_spec.name, overlay_item.environment_name)] = overlay_item.pk

    # Update or create data
    handle_record: Dict[Any, bool] = {}
    for items in [overlay_replicas, overlay_res_quotas, overlay_autoscalings]:
        # fix mypy error
        items = cast(list, items)
        for input_p in items:
            if not (proc_spec := existing_specs.get(input_p.process)):
                logger.info("Process spec not found, ignore, name: %s", input_p.process)
                continue

            # Remove duplicates by setdefault
            handle_record.setdefault((input_p.process, input_p.envName), _handlers[type(input_p)](proc_spec, input_p))
            # Move out from the index
            existing_index.pop((input_p.process, input_p.envName), None)
    for created in handle_record.values():
        ret.incr_by_created_flag(created)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ProcessSpecEnvOverlay.objects.filter(id__in=existing_index.values()).delete()
    return ret
