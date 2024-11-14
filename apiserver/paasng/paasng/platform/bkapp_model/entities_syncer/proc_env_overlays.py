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

import abc
import logging
from typing import Dict, Iterable, List, Set, Tuple, Union

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import AutoscalingOverlay, ReplicasOverlay, ResQuotaOverlay
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.modules.models import Module
from paasng.utils.structure import NotSetType

from .result import CommonSyncResult

logger = logging.getLogger(__name__)


def sync_env_overlays_replicas(
    module: Module, overlay_replicas: List[ReplicasOverlay] | NotSetType, manager: fieldmgr.FieldMgrName
) -> CommonSyncResult:
    """Sync replicas overlay data to db."""
    syncer = OverlayDataSyncer(algo=ReplicasSyncerFieldAlgo())
    return syncer.sync(module, overlay_replicas, manager)


def sync_env_overlays_res_quotas(
    module: Module, overlay_res_quotas: List[ResQuotaOverlay] | NotSetType, manager: fieldmgr.FieldMgrName
) -> CommonSyncResult:
    """Sync res_quota overlay data to db."""
    syncer = OverlayDataSyncer(algo=ResQuotasSyncerFieldAlgo())
    return syncer.sync(module, overlay_res_quotas, manager)


def sync_env_overlays_autoscalings(
    module: Module, overlay_autoscalings: List[AutoscalingOverlay] | NotSetType, manager: fieldmgr.FieldMgrName
) -> CommonSyncResult:
    """Sync autoscaling overlay data to db model"""
    syncer = OverlayDataSyncer(algo=AutoscalingSyncerFieldAlgo())
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

    :param algo: The algorithm class used for syncing.
    """

    def __init__(self, algo: "SyncerFieldAlgo"):
        self.algo = algo

    def sync(
        self,
        module: Module,
        items: Iterable[Union[ReplicasOverlay, ResQuotaOverlay, AutoscalingOverlay]] | NotSetType,
        manager: fieldmgr.FieldMgrName,
    ) -> CommonSyncResult:
        """Sync overlay data to the db."""
        ret = CommonSyncResult()
        if isinstance(items, NotSetType):
            return self._sync_notset(module, manager)

        # Build the index of existing data first to clean data later.
        existing_specs, existing_index = self._build_specs_and_index(module)

        for input_p in items:
            proc, env = input_p.process, input_p.env_name
            if not (proc_spec := existing_specs.get(proc)):
                logger.info("Process spec not found, ignore, name: %s", input_p.process)
                continue

            _, created = ProcessSpecEnvOverlay.objects.update_or_create(
                proc_spec=proc_spec, environment_name=input_p.env_name, defaults=self.algo.get_values(input_p)
            )
            ret.incr_by_created_flag(created)

            # Update the index and set the field manger
            existing_index.pop((proc, env), None)
            fieldmgr.FieldManager(module, self.algo.get_field_mgr_key(proc, env)).set(manager)

        # Reset existing data
        for pk in existing_index.values():
            ProcessSpecEnvOverlay.objects.update_or_create(pk=pk, defaults=self.algo.get_empty_values())
            ret.deleted_num += 1
        return ret

    def _sync_notset(self, module: Module, manager: fieldmgr.FieldMgrName) -> CommonSyncResult:
        """Sync when the given data is not set."""
        ret = CommonSyncResult()

        # Build the index of existing data first to clean data later.
        _, existing_index = self._build_specs_and_index(module)
        not_managed_envs = self._get_not_managed_proc_envs(module, manager, list(existing_index.keys()))

        # Reset existing data
        for (proc, env), pk in existing_index.items():
            # Do not reset the data if the environment is not managed by the current manager.
            if (proc, env) in not_managed_envs:
                continue

            ProcessSpecEnvOverlay.objects.update_or_create(pk=pk, defaults=self.algo.get_empty_values())
            # Reset the field manager too.
            fieldmgr.FieldManager(module, self.algo.get_field_mgr_key(proc, env)).reset()
            ret.deleted_num += 1
        return ret

    def _build_specs_and_index(
        self, module: Module
    ) -> Tuple[Dict[str, ModuleProcessSpec], Dict[Tuple[str, str], int]]:
        """Build the specs and index for the module.

        The index's structure: {(process name, environment name): pk}, entries whose
        value is already empty are ignored.

        :return: a tuple of (specs, index)
        """
        existing_specs = {}
        existing_index = {}
        for proc_spec in ModuleProcessSpec.objects.filter(module=module):
            existing_specs[proc_spec.name] = proc_spec
            for overlay_item in ProcessSpecEnvOverlay.objects.filter(proc_spec=proc_spec):
                if self._is_already_empty(overlay_item):
                    continue
                existing_index[(proc_spec.name, overlay_item.environment_name)] = overlay_item.pk
        return existing_specs, existing_index

    def _get_not_managed_proc_envs(
        self, module: Module, manager: fieldmgr.FieldMgrName, proc_envs: List[Tuple[str, str]]
    ) -> Set[Tuple[str, str]]:
        """Get the environments that is not managed by the current manager."""
        not_managed_envs = set()
        for process, env_name in proc_envs:
            mgr = fieldmgr.FieldManager(module, self.algo.get_field_mgr_key(process, env_name))
            if not mgr.is_managed_by(manager):
                not_managed_envs.add((process, env_name))
        return not_managed_envs

    def _is_already_empty(self, overlay_item: ProcessSpecEnvOverlay) -> bool:
        """Check if the overlay item is already empty."""
        return all(getattr(overlay_item, key) == value for key, value in self.algo.get_empty_values().items())


class SyncerFieldAlgo(abc.ABC):
    """The algorithm to sync the overlay data to the db model."""

    @abc.abstractmethod
    def get_empty_values(self) -> Dict:
        """Return the empty values for resetting the field."""

    @abc.abstractmethod
    def get_values(self, input_p) -> Dict:
        """Return the values for update or creating the field.

        :param input_p: an object has "process" and "env_name" properties.
        """

    @abc.abstractmethod
    def get_field_mgr_key(self, process: str, env: str) -> str:
        """Get the key for updating field manager."""


class ReplicasSyncerFieldAlgo(SyncerFieldAlgo):
    def get_empty_values(self) -> Dict:
        return {"target_replicas": None}

    def get_values(self, input_p) -> Dict:
        return {"target_replicas": input_p.count}

    def get_field_mgr_key(self, process: str, env: str) -> str:
        return fieldmgr.f_overlay_replicas(process, env)


class ResQuotasSyncerFieldAlgo(SyncerFieldAlgo):
    def get_empty_values(self) -> Dict:
        return {"plan_name": None}

    def get_values(self, input_p) -> Dict:
        return {"plan_name": input_p.plan}

    def get_field_mgr_key(self, process: str, env: str) -> str:
        return fieldmgr.f_overlay_res_quotas(process, env)


class AutoscalingSyncerFieldAlgo(SyncerFieldAlgo):
    def get_empty_values(self) -> Dict:
        return {"autoscaling": None, "scaling_config": None}

    def get_values(self, input_p) -> Dict:
        return {
            "autoscaling": True,
            "scaling_config": {
                "min_replicas": input_p.min_replicas,
                "max_replicas": input_p.max_replicas,
                "policy": input_p.policy,
            },
        }

    def get_field_mgr_key(self, process: str, env: str) -> str:
        return fieldmgr.f_overlay_autoscaling(process, env)
