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
from typing import List

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.controllers import ProcessesInfo
from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.bk_app.processes.readers import instance_kmodel, process_kmodel


def get_processes_info(wl_app: WlApp) -> ProcessesInfo:
    """get processes info by wl_app"""
    processes: List[Process] = []

    procs = process_kmodel.list_by_app_with_meta(wl_app)
    insts = instance_kmodel.list_by_app_with_meta(wl_app)

    for proc in procs.items:
        proc.instances = [inst for inst in insts.items if inst.process_type == proc.type]
        processes.append(proc)

    return ProcessesInfo(
        processes=processes, rv_proc=procs.get_resource_version(), rv_inst=insts.get_resource_version()
    )
