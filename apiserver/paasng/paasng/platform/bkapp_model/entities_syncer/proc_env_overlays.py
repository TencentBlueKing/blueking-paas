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
from typing import Callable, Dict, Iterable, List, Set, Tuple, Union

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import AutoscalingOverlay, ReplicasOverlay, ResQuotaOverlay
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.modules.models import Module
from paasng.utils.structure import NotSetType

from .result import CommonSyncResult

logger = logging.getLogger(__name__)


def sync_env_overlays_replicas(
    module: Module, overlay_replicas: List[ReplicasOverlay] | NotSetType, manager: fieldmgr.ManagerType
) -> CommonSyncResult:
    """Sync replicas overlay data to db."""
    syncer = OverlayDataSyncer(
        empty_defaults_value={"target_replicas": None},
        defaults_value_getter=lambda input_p: {"target_replicas": input_p.count},
        field_mgr_key_func=fieldmgr.f_overlay_replicas,
    )
    return syncer.sync(module, overlay_replicas, manager)


def sync_env_overlays_res_quotas(
    module: Module, overlay_res_quotas: List[ResQuotaOverlay] | NotSetType, manager: fieldmgr.ManagerType
) -> CommonSyncResult:
    """Sync res_quota overlay data to db."""
    syncer = OverlayDataSyncer(
        empty_defaults_value={"plan_name": None},
        defaults_value_getter=lambda input_p: {"plan_name": input_p.plan},
        field_mgr_key_func=fieldmgr.f_overlay_res_quotas,
    )
    return syncer.sync(module, overlay_res_quotas, manager)


def sync_env_overlays_autoscalings(
    module: Module, overlay_autoscalings: List[AutoscalingOverlay] | NotSetType, manager: fieldmgr.ManagerType
) -> CommonSyncResult:
    """Sync autoscaling overlay data to db model"""

    def _value_getter(input_p):
        return {
            "autoscaling": True,
            "scaling_config": {
                "min_replicas": input_p.min_replicas,
                "max_replicas": input_p.max_replicas,
                "policy": input_p.policy,
            },
        }

    syncer = OverlayDataSyncer(
        empty_defaults_value={"autoscaling": None, "scaling_config": None},
        defaults_value_getter=_value_getter,
        field_mgr_key_func=fieldmgr.f_overlay_replicas,
    )
    return syncer.sync(module, overlay_autoscalings, manager)


def clean_empty_overlays(module):
    """Clean up overlay records that contains empty data."""
    empty_values = {"autoscaling": None, "scaling_config": None, "target_replicas": None, "plan_name": None}

    # If new fields were added to the module, the clean up process should abort to avoid data loss.
    fields = {f.name for f in ProcessSpecEnvOverlay._meta.fields}
    if set(fields) - set(empty_values) != {"id", "region", "proc_spec", "updated", "environment_name", "created"}:
        raise RuntimeError("unexpected fields found on ProcessSpecEnvOverlay")

    for proc_spec in ModuleProcessSpec.objects.filter(module=module):
        for overlay_item in ProcessSpecEnvOverlay.objects.filter(proc_spec=proc_spec):
            if all(getattr(overlay_item, key) == value for key, value in empty_values.items()):
                overlay_item.delete()


class OverlayDataSyncer:
    """Sync overlay data to db model.

    :param empty_defaults_value: The empty default value, used to reset the data.
    :param defaults_value_getter: A function to get the default value as a dict for upsert.
    :param field_mgr_key_func: A function to get the field manager key.
    """

    def __init__(
        self,
        empty_defaults_value: Dict,
        defaults_value_getter: Callable,
        field_mgr_key_func: Callable[[str, str], str],
    ):
        self.empty_defaults_value = empty_defaults_value
        self.defaults_value_getter = defaults_value_getter
        self.field_mgr_key_func = field_mgr_key_func

    def sync(
        self,
        module: Module,
        items: Iterable[Union[ReplicasOverlay, ResQuotaOverlay, AutoscalingOverlay]] | NotSetType,
        manager: fieldmgr.ManagerType,
    ) -> CommonSyncResult:
        """Sync overlay data to the db."""
        ret = CommonSyncResult()
        if isinstance(items, NotSetType):
            items = []

        # Build the index of existing data first to clean data later.
        # Data structure: {(process name, environment name): pk}, contains not none
        # data on the sub_field.
        existing_index = {}
        existing_specs = {}
        for proc_spec in ModuleProcessSpec.objects.filter(module=module):
            existing_specs[proc_spec.name] = proc_spec
            for overlay_item in ProcessSpecEnvOverlay.objects.filter(proc_spec=proc_spec):
                if self.is_already_empty(overlay_item):
                    continue
                existing_index[(proc_spec.name, overlay_item.environment_name)] = overlay_item.pk

        not_managed_envs = self.get_not_managed_proc_envs(module, manager, list(existing_index.keys()))

        for input_p in items:
            proc, env = input_p.process, input_p.env_name
            if not (proc_spec := existing_specs.get(proc)):
                logger.info("Process spec not found, ignore, name: %s", input_p.process)
                continue

            _, created = ProcessSpecEnvOverlay.objects.update_or_create(
                proc_spec=proc_spec, environment_name=input_p.env_name, defaults=self.defaults_value_getter(input_p)
            )
            ret.incr_by_created_flag(created)

            # Update the index and set the field manger
            existing_index.pop((proc, env), None)
            fieldmgr.FieldManager(module, self.field_mgr_key_func(proc, env)).set(manager)

        # Reset existing data
        for (proc, env), pk in existing_index.items():
            # Do not reset the data if the environment is not managed by the current manager.
            if (proc, env) in not_managed_envs:
                continue

            ProcessSpecEnvOverlay.objects.update_or_create(pk=pk, defaults=self.empty_defaults_value)
            ret.deleted_num += 1
        return ret

    def get_not_managed_proc_envs(
        self, module: Module, manager: fieldmgr.ManagerType, proc_envs: List[Tuple[str, str]]
    ) -> Set[Tuple[str, str]]:
        """Get the environments that is not managed by the current manager."""
        not_managed_envs = set()
        for process, env_name in proc_envs:
            mgr = fieldmgr.FieldManager(module, self.field_mgr_key_func(process, env_name))
            if not mgr.is_managed_by(manager):
                not_managed_envs.add((process, env_name))
        return not_managed_envs

    def is_already_empty(self, overlay_item: ProcessSpecEnvOverlay) -> bool:
        """Check if the overlay item is already empty."""
        return all(getattr(overlay_item, key) == value for key, value in self.empty_defaults_value.items())
