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

from dataclasses import asdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

from django.conf import settings

from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.modules.models import Module
from paasng.platform.modules.models.deploy_config import HookList

PROC_DEFAULT_REPLICAS = 1


class AttrSetter:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.changed = False

    def setattr(self, name, value):
        setattr(self.wrapped, name, value)
        self.changed = True


class ModuleProcessSpecManager:
    """The manager for ModuleProcessSpec objects."""

    def __init__(self, module: Module):
        self.module = module

    def sync_from_desc(self, processes: List[ProcessTmpl]):  # noqa: C901
        """Sync ProcessSpecs data with given processes.

        :param processes: process spec structure defined in the form BkAppProcess ProcessTmpl
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """

        processes_map: Dict[str, ProcessTmpl] = {process.name: process for process in processes}

        # remove proc spec objects which is already deleted via procfile
        self.delete_outdated_procs(cur_procs_name=processes_map.keys())

        existed_proc_specs = ModuleProcessSpec.objects.filter(module=self.module)
        existed_procs_name = {p.name for p in existed_proc_specs}

        # add spec objects start
        adding_procs = [process for name, process in processes_map.items() if name not in existed_procs_name]

        def process_spec_builder(process: ProcessTmpl) -> ModuleProcessSpec:
            spec = ModuleProcessSpec(
                module=self.module,
                name=process.name,
                proc_command=process.command,
                target_replicas=process.replicas or PROC_DEFAULT_REPLICAS,
                plan_name=process.plan or ResQuotaPlan.P_DEFAULT,
                probes=process.probes,
                services=process.services,
            )
            # 创建时, 分环境设置副本数
            for app_env_name in AppEnvName.get_values():
                target_replicas = process.replicas or self.get_default_replicas(name, app_env_name)
                if target_replicas != spec.target_replicas:
                    ProcessSpecEnvOverlay.objects.update_or_create(
                        proc_spec=spec,
                        environment_name=AppEnvName(app_env_name).value,
                        defaults={"target_replicas": target_replicas},
                    )
            return spec

        self.bulk_create_procs(proc_creator=process_spec_builder, adding_procs=adding_procs)
        # add spec objects end

        # update spec objects start
        updating_procs = [process for name, process in processes_map.items() if name in existed_procs_name]

        def process_spec_updator(process: ProcessTmpl) -> Tuple[bool, ModuleProcessSpec]:
            process_spec = existed_proc_specs.get(name=process.name)
            recorder = AttrSetter(process_spec)
            if process_spec.proc_command != process.command:
                recorder.setattr("proc_command", process.command)
            if process.plan and process_spec.plan_name != process.plan:
                recorder.setattr("plan_name", process.plan)
            if process.replicas and process_spec.target_replicas != process.replicas:
                recorder.setattr("target_replicas", process.replicas)

            if process.probes and process_spec.probes != process.probes:
                recorder.setattr("probes", process.probes)

            if process.services and process_spec.services != process.services:
                recorder.setattr("services", process.services)

            return recorder.changed, process_spec

        self.bulk_update_procs(
            proc_updator=process_spec_updator,
            updating_procs=updating_procs,
            updated_fields=["proc_command", "target_replicas", "plan_name", "services", "probes", "updated"],
        )
        # update spec objects end

        # 根据环境, 设置副本数
        for name, process in processes_map.items():
            for env_name in AppEnvName.get_values():
                # 只有设置了有效副本数, 才更新, 否则不更新(使用已设置的副本数)
                if process.replicas:
                    self.set_replicas(name, env_name, process.replicas)

    def delete_outdated_procs(self, cur_procs_name: Iterable[str]):
        """Delete all ModuleProcessSpec not existed in cur_procs_name"""
        proc_specs = ModuleProcessSpec.objects.filter(module=self.module)
        existed_procs_name = set(proc_specs.values_list("name", flat=True))
        # remove proc spec objects which is already deleted via procfile
        removing_procs_name = list(existed_procs_name - set(cur_procs_name))
        if removing_procs_name:
            proc_specs.filter(name__in=removing_procs_name).delete()

    def bulk_create_procs(
        self,
        proc_creator: Callable[[ProcessTmpl], ModuleProcessSpec],
        adding_procs: List[ProcessTmpl],
    ):
        """bulk create ModuleProcessSpec

        :param proc_creator: ModuleProcessSpec factory, accept `process` and return ModuleProcessSpec
        :param adding_procs: `process` waiting to transform to ModuleProcessSpec
        """
        spec_create_bulks: List[ModuleProcessSpec] = []
        for process in adding_procs:
            spec_create_bulks.append(proc_creator(process))  # type: ignore
        if spec_create_bulks:
            ModuleProcessSpec.objects.bulk_create(spec_create_bulks)

    def bulk_update_procs(
        self,
        proc_updator: Callable[[ProcessTmpl], Tuple[bool, ModuleProcessSpec]],
        updating_procs: List[ProcessTmpl],
        updated_fields: List[str],
    ):
        spec_update_bulks: List[ModuleProcessSpec] = []
        for process in updating_procs:
            changed, updated = proc_updator(process)  # type: ignore
            if changed:
                spec_update_bulks.append(updated)
        if spec_update_bulks:
            ModuleProcessSpec.objects.bulk_update(spec_update_bulks, updated_fields)

    def set_replicas(self, proc_name: str, env_name: str, replicas: int):
        """Set the replicas for the given process and environment."""
        proc_spec = ModuleProcessSpec.objects.get(module=self.module, name=proc_name)
        if proc_spec.get_target_replicas(env_name) != replicas:
            ProcessSpecEnvOverlay.objects.update_or_create(
                proc_spec=proc_spec,
                environment_name=AppEnvName(env_name).value,
                defaults={"target_replicas": replicas},
            )

    def set_autoscaling(
        self, proc_name: str, env_name: str, enabled: bool, config: Optional[AutoscalingConfig] = None
    ):
        """Set the autoscaling for the given process and environment."""
        proc_spec = ModuleProcessSpec.objects.get(module=self.module, name=proc_name)
        defaults: Dict[str, Union[bool, Dict, None]] = {"autoscaling": enabled}
        if config is not None:
            defaults.update(scaling_config=asdict(config))

        ProcessSpecEnvOverlay.objects.update_or_create(
            proc_spec=proc_spec,
            environment_name=AppEnvName(env_name).value,
            defaults=defaults,
        )

    @staticmethod
    def get_default_replicas(process_type: str, environment: str):
        """Get default replicas for current process type"""
        return settings.ENGINE_PROC_REPLICAS_BY_TYPE.get((process_type, environment), PROC_DEFAULT_REPLICAS)


def sync_hooks(module: Module, hooks: HookList):
    """sync HookList to ModuleDeployHook"""
    # Build the index of existing data first to remove data later.
    # Data structure: {hook type: pk}
    existing_index = {}
    for hook in module.deploy_hooks.all():
        existing_index[hook.type] = hook.pk

    for hook in hooks:
        if hook.enabled:
            module.deploy_hooks.enable_hook(type_=hook.type, proc_command=hook.get_proc_command())
            # Move out from the index
            existing_index.pop(hook.type, None)

    # Remove existing data that is not touched.
    module.deploy_hooks.filter(id__in=existing_index.values()).delete()
