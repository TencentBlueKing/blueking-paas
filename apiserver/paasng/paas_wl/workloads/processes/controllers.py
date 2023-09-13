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
import datetime
import logging
from typing import List, NamedTuple

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from paas_wl.cnative.specs.procs import get_procfile
from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models import Release, WlApp
from paas_wl.workloads.processes.entities import Process
from paas_wl.workloads.processes.exceptions import ProcessOperationTooOften
from paas_wl.workloads.processes.models import ProcessSpec
from paas_wl.workloads.processes.readers import instance_kmodel, ns_instance_kmodel, ns_process_kmodel, process_kmodel
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def judge_operation_frequent(app: WlApp, proc_type: str, operation_interval: datetime.timedelta):
    """检查 process 操作是否频繁

    - Only normal app which owns ProcessSpec objects is supported
    - Last operated time was stored in ProcessSpec.updated
    """
    try:
        spec = ProcessSpec.objects.get(engine_app_id=app.uuid, name=proc_type)
    except ProcessSpec.DoesNotExist:
        return

    if (timezone.now() - spec.updated) < operation_interval:
        raise ProcessOperationTooOften(_(f"进程操作过于频繁，请间隔 {operation_interval.total_seconds()} 秒再试。"))


class ProcessesInfo(NamedTuple):
    """real-time processes info"""

    processes: List[Process]
    rv_proc: str
    rv_inst: str


def list_ns_processes(cluster_name: str, namespace: str) -> ProcessesInfo:
    """list the real-time processes in given namespace"""
    processes: List[Process] = []

    procs_in_k8s = ns_process_kmodel.list_by_ns_with_mdata(cluster_name, namespace)
    insts_in_k8s = ns_instance_kmodel.list_by_ns_with_mdata(cluster_name, namespace)
    for process in procs_in_k8s.items:
        process.instances = [
            inst for inst in insts_in_k8s.items if inst.process_type == process.type and inst.app == process.app
        ]
        if len(process.instances) == 0:
            logger.debug("Process %s have no instances", process.type)
            continue
        processes.append(process)

    return ProcessesInfo(
        processes=processes,
        rv_proc=procs_in_k8s.get_resource_version(),
        rv_inst=insts_in_k8s.get_resource_version(),
    )


def list_processes(env: ModuleEnvironment) -> ProcessesInfo:
    """list the real-time processes of given env


    1. Get current process structure
        1.1 for default apps, will get process structure from `release.structure`
        1.2 for cnative apps, will get process structure from app model resource
    2. Get process status from `process_kmodel` & `instance_kmodel`
    """
    processes: List[Process] = []
    procfile = {}

    wl_app = env.wl_app
    if wl_app.type == WlAppType.CLOUD_NATIVE:
        procfile = get_procfile(env)
    else:
        try:
            release: Release = Release.objects.get_latest(wl_app)
            procfile = release.get_procfile()
        except Release.DoesNotExist:
            logger.warning("Not any available Release")

    procs_in_k8s = process_kmodel.list_by_app_with_meta(wl_app)
    insts_in_k8s = instance_kmodel.list_by_app_with_meta(wl_app)
    for process in procs_in_k8s.items:
        process.instances = [inst for inst in insts_in_k8s.items if inst.process_type == process.type]
        processes.append(process)

    if missing := procfile.keys() - {process.type for process in processes}:
        logger.warning("Process %s in procfile missing in k8s cluster", missing)
    return ProcessesInfo(
        processes=processes,
        rv_proc=procs_in_k8s.get_resource_version(),
        rv_inst=insts_in_k8s.get_resource_version(),
    )
