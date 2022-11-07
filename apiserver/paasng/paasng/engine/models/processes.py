# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

import cattr
from attrs import define

from paasng.engine.controller.state import controller_client
from paasng.engine.models import EngineApp

if TYPE_CHECKING:
    from paasng.engine.controller.client import ControllerClient

logger = logging.getLogger(__name__)


@define
class Instance:
    """An Process instance object"""

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

    def __init__(self, app: EngineApp, ctl_client: Optional['ControllerClient'] = None):
        self.app = app
        self.ctl_client = ctl_client or controller_client

    def sync_processes_specs(self, processes: List[Dict]):
        """Sync specs by plain ProcessSpec structure

        :param processes: plain process spec structure,
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """
        self.ctl_client.sync_processes_specs(self.app.region, self.app.name, processes)

    def list_processes_specs(self, target_status: Optional[str] = None) -> List[Dict]:
        """Get specs of current app's all processes

        :param target_status: if given, filter results by given target_status
        """
        specs = self.ctl_client.list_processes_specs(self.app.region, self.app.name)
        results = []
        for item in specs:
            # Filter by given conditions
            if target_status and item['target_status'] != target_status:
                continue
            results.append(item)
        return results

    def list_processes(self) -> List[Process]:
        """Query all running processes"""
        resp = self.ctl_client.list_processes_statuses(region=self.app.region, app_name=self.app.name)
        raw_processes = resp.get('results', [])
        return [cattr.structure(x, Process) for x in raw_processes]

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
        return self.ctl_client.create_webconsole(
            region=self.app.region,
            app_name=self.app.name,
            process_type=process_type,
            process_instance=process_instance_name,
            container_name=container_name,
            operator=operator,
            command=command,
        )
