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

import logging
from typing import Any, Callable, Dict, List, Type, cast

from paasng.platform.bkapp_model.entities import AutoscalingOverlay, ProcEnvOverlay, ReplicasOverlay, ResQuotaOverlay
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.modules.models import Module

from .result import CommonSyncResult

logger = logging.getLogger(__name__)


def _upsert_replicas(proc_spec: ModuleProcessSpec, input_p: ReplicasOverlay) -> bool:
    """save ReplicasOverlay item"""
    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec, environment_name=input_p.env_name, defaults={"target_replicas": input_p.count}
    )
    return created


def _upsert_res_quota(proc_spec: ModuleProcessSpec, input_p: ResQuotaOverlay) -> bool:
    """save ResQuotaOverlay item"""
    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec, environment_name=input_p.env_name, defaults={"plan_name": input_p.plan}
    )
    return created


def _upsert_autoscaling(proc_spec: ModuleProcessSpec, input_p: AutoscalingOverlay) -> bool:
    """save AutoscalingOverlay item"""
    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec,
        environment_name=input_p.env_name,
        defaults={
            "autoscaling": True,
            "scaling_config": {
                "min_replicas": input_p.min_replicas,
                "max_replicas": input_p.max_replicas,
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


def sync_proc_env_overlays(
    module: Module,
    overlay_replicas: List[ReplicasOverlay],
    overlay_res_quotas: List[ResQuotaOverlay],
    overlay_autoscalings: List[AutoscalingOverlay],
) -> CommonSyncResult:
    """Sync multiple processes overlay data to db model

    :param overlay_replicas: A list of ResQuotaOverlay items.
    :param overlay_res_quotas: A list of ResQuotaOverlay items.
    :param overlay_autoscalings: A list of AutoscalingOverlay items.
    :return: sync result.
    """
    ret = CommonSyncResult()

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

            # Update the column by handler function and store the created flag
            handle_record.setdefault((input_p.process, input_p.env_name), _handlers[type(input_p)](proc_spec, input_p))
            # Move out from the index
            existing_index.pop((input_p.process, input_p.env_name), None)

    for created in handle_record.values():
        ret.incr_by_created_flag(created)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ProcessSpecEnvOverlay.objects.filter(id__in=existing_index.values()).delete()
    return ret


def sync_env_overlay_by_proc(module, proc_name: str, proc_env_overlay: ProcEnvOverlay) -> CommonSyncResult:
    """Sync proc_env_overlay to ProcessSpecEnvOverlay(db model) by one process. It will update or create
    ProcessSpecEnvOverlay by one process, not delete.

    :param module: module
    :param proc_name: process name to set env_overlay
    :param proc_env_overlay: proc env_overlay data
    :return: sync result
    """

    ret = CommonSyncResult()

    proc_spec = ModuleProcessSpec.objects.get(module=module, name=proc_name)

    _, created = ProcessSpecEnvOverlay.objects.update_or_create(
        proc_spec=proc_spec,
        environment_name=proc_env_overlay.env_name,
        defaults={
            "target_replicas": proc_env_overlay.target_replicas,
            "plan_name": proc_env_overlay.plan_name,
            "autoscaling": proc_env_overlay.autoscaling,
            "scaling_config": proc_env_overlay.scaling_config.dict() if proc_env_overlay.scaling_config else None,
        },
    )
    ret.incr_by_created_flag(created)

    return ret
