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
import logging
from dataclasses import asdict
from typing import Dict, List, Optional

import cattr
from attrs import define
from django.utils.functional import cached_property

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.platform.applications.models.app import WLEngineApp
from paas_wl.resources.base.bcs_client import BCSClient
from paas_wl.workloads.processes.controllers import get_processes_status, list_proc_specs
from paas_wl.workloads.processes.models import ProcessSpecManager
from paas_wl.workloads.processes.readers import process_kmodel
from paasng.engine.models import EngineApp

logger = logging.getLogger(__name__)


@define
class Instance:
    """A Process instance object"""

    name: str
    host_ip: str
    start_time: str
    state: str
    ready: bool
    image: str
    restart_count: int
    version: int
    process_type: Optional[str] = None
    namespace: Optional[str] = None

    def __str__(self):
        return f'Instance<{self.name}-{self.state}>'


@define
class Process:
    """
    Q: What's the differences between Process and ProcessSpec?
    A: Process represents the actual data from engine backend, and ProcessSpec represents the expectation of user.
    """

    type: str
    app_name: str
    version: int
    command: str
    process_status: Dict
    desired_replicas: str
    instances: List[Instance]

    @property
    def available_instance_count(self):
        return len([instance for instance in self.instances if instance.ready and instance.version == self.version])

    @property
    def engine_app_name(self):
        return self.app_name

    def __repr__(self):
        return f'Process<{self.type}>'


class ProcessManager:
    """Manager for engine processes"""

    def __init__(self, app: EngineApp):
        self.app = app

    @cached_property
    def wl_app(self) -> WLEngineApp:
        return self.app.to_wl_obj()

    def sync_processes_specs(self, processes: List[Dict]):
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
        specs = list_proc_specs(self.wl_app)
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
        manager = ProcessManager(self.app)
        images = {instance.image for process in manager.list_processes() for instance in process.instances}
        if len(images) == 0:
            raise RuntimeError(f"Can't find running image for App<{self.app}>")
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
