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
from dataclasses import asdict
from typing import Dict, List, Optional

import cattr
from django.utils.functional import cached_property

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.cnative.specs.procs import get_proc_specs
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.base.bcs_client import BCSClient
from paas_wl.workloads.processes.controllers import get_processes_status
from paas_wl.workloads.processes.drf_serializers import CNativeProcSpecSLZ, ProcessSpecSLZ
from paas_wl.workloads.processes.models import ProcessSpecManager, ProcessTmpl
from paas_wl.workloads.processes.processes import Process
from paas_wl.workloads.processes.readers import process_kmodel
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import ModuleEnvironment


def _list_proc_specs(env: ModuleEnvironment) -> List[Dict]:
    """Return all processes specs of an app

    :return: list of process specs
    """
    # TODO: 统一返回值的字段？
    if env.application.type == ApplicationType.CLOUD_NATIVE:
        return CNativeProcSpecSLZ(get_proc_specs(env), many=True).data
    wl_app = env.wl_app
    return ProcessSpecSLZ(wl_app.process_specs.all(), many=True).data


class ProcessManager:
    """Manager for engine processes"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    @cached_property
    def wl_app(self) -> WlApp:
        return self.env.wl_app

    def sync_processes_specs(self, processes: List[ProcessTmpl]):
        """Sync specs by plain ProcessSpec structure

        :param processes: plain process spec structure,
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """
        ProcessSpecManager(self.wl_app).sync(processes)

    def list_processes_specs(self, target_status: Optional[str] = None) -> List[Dict]:
        """Get specs of current app's all processes

        :param target_status: if given, filter results by given target_status
        """
        specs = _list_proc_specs(self.env)
        results = []
        for item in specs:
            # Filter by given conditions
            if target_status and item['target_status'] != target_status:
                continue
            results.append(item)
        return results

    def list_processes(self) -> List[Process]:
        """Query all running processes"""
        proc_status = get_processes_status(self.wl_app)
        items = []
        for proc in proc_status:
            items.append(
                {
                    'type': proc.type,
                    'app_name': proc.app.name,
                    'instances': [asdict(inst) for inst in proc.instances],
                    'command': proc.runtime.proc_command,
                    'process_status': proc.status.to_dict() if proc.status else {},
                    'desired_replicas': proc.replicas,
                    'version': proc.version,
                }
            )
        return [cattr.structure(x, Process) for x in items]

    def get_running_image(self) -> str:
        images = {instance.image for process in self.list_processes() for instance in process.instances}
        if len(images) == 0:
            raise RuntimeError(f"Can't find running image for Env<{self.env}>")
        elif len(images) > 1:
            raise RuntimeError("multiple image found!")
        return images.pop()

    def create_webconsole(
        self, operator: str, process_type: str, process_instance_name: str, container_name=None, command="bash"
    ):
        """Create a webconsole provided by bcs"""
        if not container_name:
            container_name = process_kmodel.get_by_type(self.wl_app, type=process_type).main_container_name

        cluster = get_cluster_by_app(self.wl_app)
        return BCSClient().api.create_web_console_sessions(
            json={
                'namespace': self.wl_app.namespace,
                'pod_name': process_instance_name,
                'container_name': container_name,
                'command': command,
                'operator': operator,
            },
            path_params={
                'cluster_id': cluster.bcs_cluster_id,
                'project_id_or_code': cluster.bcs_project_id,
                'version': 'v4',
            },
        )
