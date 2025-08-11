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

from typing import Any, Dict, Iterable, List

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.entities import Process
from paasng.platform.bkapp_model.entities.scaling_config import AutoscalingConfig
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.modules.models import Module
from paasng.utils.structure import NOTSET, NotSetType

from .result import CommonSyncResult


def sync_processes(
    module: Module, processes: List[Process], manager: fieldmgr.FieldMgrName, use_proc_command: bool = False
) -> CommonSyncResult:
    """sync processes data to ModuleProcessSpec(db model)

    :param module: app module
    :param processes: processes list
    :param manager: the manager performing the sync action.
    :param use_proc_command: only update the "proc_command" field, ignore "command"
        and "args", when the processes data is provided by legacy desc file, this
        argument should be set to True.
    :return: sync result
    """
    ret = CommonSyncResult()

    # Build the index of existing data first to remove data later.
    # Data structure: {process name: pk}
    existing_index = {}
    for proc_spec in ModuleProcessSpec.objects.filter(module=module):
        existing_index[proc_spec.name] = proc_spec.pk

    managed_values = ManagedFieldValues(module, processes, manager, set(existing_index.keys()))
    target_replicas_map, r_reset_procs = managed_values.get_target_replicas()
    autoscaling_map, a_reset_procs = managed_values.get_autoscaling()

    # Update or create data
    for process in processes:
        defaults: Dict[str, Any] = {
            "proc_command": process.proc_command,
            "port": process.target_port,
            "plan_name": process.res_quota_plan or ResQuotaPlan.P_DEFAULT,
            "probes": process.probes,
            "services": process.services,
            "tenant_id": module.tenant_id,
            "components": process.components,
        }
        if not use_proc_command:
            defaults.update({"command": process.command, "args": process.args})
        if process.name in target_replicas_map:
            defaults.update({"target_replicas": target_replicas_map[process.name]})
        if process.name in autoscaling_map:
            as_config = autoscaling_map[process.name]
            defaults.update({"autoscaling": bool(as_config), "scaling_config": as_config})

        _, created = ModuleProcessSpec.objects.update_or_create(module=module, name=process.name, defaults=defaults)

        ret.incr_by_created_flag(created)
        # Move out from the index
        existing_index.pop(process.name, None)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ModuleProcessSpec.objects.filter(module=module, id__in=existing_index.values()).delete()

    # Set and reset field managers
    managed_values.set_field_mgr_target_replicas(target_replicas_map.keys())
    managed_values.reset_field_mgr_target_replicas(r_reset_procs)

    managed_values.set_field_mgr_autoscaling(autoscaling_map.keys())
    managed_values.reset_field_mgr_autoscaling(a_reset_procs)
    return ret


class ManagedFieldValues:
    """This class helps to get the values of the fields that respects the field management
    status, for example, if the "replicas" field is managed by managers other than "APP_DESC"
    and the input is NOTSET, current class will skip the process when producing values.
    """

    default_replicas = 1

    def __init__(
        self, module: Module, processes: List[Process], manager: fieldmgr.FieldMgrName, existing_procs: set[str]
    ):
        self.module = module
        self.processes = processes
        self.manager = manager
        self.existing_procs = existing_procs

    def get_target_replicas(self) -> tuple[dict[str, int], set[str]]:
        """Get the target replicas for each process.

        :return: A tuple, the first item is a dict of process name to replicas, the
            second item is the process names that have been reset by the NOTSET value.
        """
        results: dict[str, int] = {}
        reset_procs = set()
        for process in self.processes:
            name = process.name
            replicas_mgr = fieldmgr.FieldManager(
                self.module, fieldmgr.f_proc_replicas(name), default_manager=fieldmgr.FieldMgrName.WEB_FORM
            )
            if (
                not replicas_mgr.can_be_managed_by(self.manager)
                and process.replicas == NOTSET
                and name in self.existing_procs
            ):
                continue

            if isinstance(process.replicas, NotSetType):
                reset_procs.add(name)
                results[name] = self.default_replicas
            else:
                results[name] = self.default_replicas if process.replicas is None else process.replicas
        return results, reset_procs

    def set_field_mgr_target_replicas(self, names: Iterable[str]):
        """Set the field manager for the target replicas field."""
        fieldmgr.MultiFieldsManager(self.module).set_many(
            [fieldmgr.f_proc_replicas(name) for name in names], self.manager
        )

    def reset_field_mgr_target_replicas(self, names: Iterable[str]):
        """Reset the field manager for the target replicas field."""
        fieldmgr.MultiFieldsManager(self.module).reset_many([fieldmgr.f_proc_replicas(name) for name in names])

    def get_autoscaling(self) -> tuple[dict[str, AutoscalingConfig | None], set[str]]:
        """Get the autoscaling config for each process.

        :return: A tuple, the first item is a dict of process name to autoscaling config,
            the second item is the process names that have been reset by the NOTSET value.
        """
        results: dict[str, AutoscalingConfig | None] = {}
        reset_procs = set()
        for process in self.processes:
            name = process.name
            autoscaling_mgr = fieldmgr.FieldManager(
                self.module, fieldmgr.f_proc_autoscaling(name), default_manager=fieldmgr.FieldMgrName.WEB_FORM
            )
            if isinstance(process.autoscaling, NotSetType) and not autoscaling_mgr.can_be_managed_by(self.manager):
                continue

            if isinstance(process.autoscaling, NotSetType):
                reset_procs.add(name)
                results[name] = None
            else:
                results[name] = process.autoscaling
        return results, reset_procs

    def set_field_mgr_autoscaling(self, names: Iterable[str]):
        """Set the field manager for the autoscaling field."""
        fieldmgr.MultiFieldsManager(self.module).set_many(
            [fieldmgr.f_proc_autoscaling(name) for name in names], self.manager
        )

    def reset_field_mgr_autoscaling(self, names: Iterable[str]):
        """reset the field manager for the autoscaling field."""
        fieldmgr.MultiFieldsManager(self.module).reset_many([fieldmgr.f_proc_autoscaling(name) for name in names])
