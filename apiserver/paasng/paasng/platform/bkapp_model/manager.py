# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Callable, Dict, Iterable, List, Tuple, Union

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.modules.models import Module

PROC_DEFAULT_REPLICAS = 1


class AttrSetter:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.changed = False

    def setattr(self, name, value):
        setattr(self.wrapped, name, value)
        self.changed = True


class ModuleProcessSpecManager:
    def __init__(self, module: Module):
        self.module = module

    def sync_form_bkapp(self, processes: List['BkAppProcess']):
        """Sync ProcessSpecs data with given processes.

        :param processes: process spec structure defined in the form BkAppProcess
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """
        processes_map: Dict[str, 'BkAppProcess'] = {process.name: process for process in processes}

        # delete outdated procs, which are removed from bkapp
        self.delete_outdated_procs(cur_procs_name=processes_map.keys())

        existed_proc_specs = ModuleProcessSpec.objects.filter(module=self.module)
        existed_procs_name = {p.name for p in existed_proc_specs}

        # add spec objects start
        adding_procs = [process for name, process in processes_map.items() if name not in existed_procs_name]

        def process_spec_builder(process: BkAppProcess) -> ModuleProcessSpec:
            return ModuleProcessSpec(
                module=self.module,
                name=process.name,
                command=process.command,
                args=process.args,
                port=process.targetPort,
                target_replicas=process.replicas,
                plan_name=process.resQuotaPlan,
                # Deprecated: 仅用于 v1alpha1 的云原生应用
                image=process.image,
                image_pull_policy=process.imagePullPolicy,
                # TODO: set image_credential_name
                # image_credential_name=""
            )

        self.bulk_create_procs(proc_creator=process_spec_builder, adding_procs=adding_procs)
        # add spec objects end

        # update spec objects start
        updating_procs = [process for name, process in processes_map.items() if name in existed_procs_name]

        def process_spec_updator(process: BkAppProcess) -> Tuple[bool, ModuleProcessSpec]:
            process_spec = existed_proc_specs.get(name=process.name)
            recorder = AttrSetter(process_spec)
            if process_spec.command != process.command:
                recorder.setattr("command", process.command)
            if process_spec.args != process.args:
                recorder.setattr("args", process.args)
            if process_spec.target_replicas != process.replicas:
                recorder.setattr("target_replicas", process.replicas)
            if process.resQuotaPlan and process_spec.plan_name != process.resQuotaPlan:
                recorder.setattr("plan_name", process.resQuotaPlan)
            return recorder.changed, process_spec

        self.bulk_update_procs(
            proc_updator=process_spec_updator,
            updating_procs=updating_procs,
            updated_fields=["command", "args", "target_replicas", "plan_name", "updated"],
        )
        # update spec objects end

    def sync_from_desc(self, processes: List['ProcessTmpl']):
        """Sync ProcessSpecs data with given processes.

        :param processes: process spec structure defined in the form BkAppProcess ProcessTmpl
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """

        processes_map: Dict[str, 'ProcessTmpl'] = {process.name: process for process in processes}

        # remove proc spec objects which is already deleted via procfile
        self.delete_outdated_procs(cur_procs_name=processes_map.keys())

        existed_proc_specs = ModuleProcessSpec.objects.filter(module=self.module)
        existed_procs_name = {p.name for p in existed_proc_specs}

        # add spec objects start
        adding_procs = [process for name, process in processes_map.items() if name not in existed_procs_name]

        def process_spec_builder(process: ProcessTmpl) -> ModuleProcessSpec:
            return ModuleProcessSpec(
                module=self.module,
                name=process.name,
                proc_command=process.command,
                target_replicas=process.replicas or PROC_DEFAULT_REPLICAS,
                plan_name=process.plan or ResQuotaPlan.P_DEFAULT,
            )

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
            return recorder.changed, process_spec

        self.bulk_update_procs(
            proc_updator=process_spec_updator,
            updating_procs=updating_procs,
            updated_fields=["proc_command", "target_replicas", "plan_name", "updated"],
        )
        # update spec objects end

    def delete_outdated_procs(self, cur_procs_name: Iterable[str]):
        """Delete all ModuleProcessSpec not existed in cur_procs_name"""
        proc_specs = ModuleProcessSpec.objects.filter(module=self.module)
        existed_procs_name = set(proc_specs.values_list('name', flat=True))
        # remove proc spec objects which is already deleted via procfile
        removing_procs_name = list(existed_procs_name - set(cur_procs_name))
        if removing_procs_name:
            proc_specs.filter(name__in=removing_procs_name).delete()

    def bulk_create_procs(
        self,
        proc_creator: Union[Callable[[ProcessTmpl], ModuleProcessSpec], Callable[[BkAppProcess], ModuleProcessSpec]],
        adding_procs: Union[List[ProcessTmpl], List[BkAppProcess]],
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
        proc_updator: Union[
            Callable[[ProcessTmpl], Tuple[bool, ModuleProcessSpec]],
            Callable[[BkAppProcess], Tuple[bool, ModuleProcessSpec]],
        ],
        updating_procs: Union[List[ProcessTmpl], List[BkAppProcess]],
        updated_fields: List[str],
    ):
        spec_update_bulks: List[ModuleProcessSpec] = []
        for process in updating_procs:
            changed, updated = proc_updator(process)  # type: ignore
            if changed:
                spec_update_bulks.append(updated)
        if spec_update_bulks:
            ModuleProcessSpec.objects.bulk_update(spec_update_bulks, updated_fields)
