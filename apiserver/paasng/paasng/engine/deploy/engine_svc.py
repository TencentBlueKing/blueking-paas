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
"""Engine services module
"""
import datetime
from typing import Dict, List, TypedDict

from django.utils.functional import cached_property

from paas_wl.platform.applications.constants import ArtifactType
from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.models.build import Build, BuildProcess
from paas_wl.workloads.images.models import AppImageCredential
from paasng.engine.models.deployment import Deployment


class LogLine(TypedDict):
    stream: str
    line: str
    created: datetime.datetime


def polish_line(line: str) -> str:
    """Return the line with special characters removed"""
    return line.replace('\x1b[1G', '')


def get_all_logs(d: Deployment) -> str:
    """Get all logs of current deployment, command and error detail are included.

    :param d: The Deployment object
    :return: All logs of the current deployment
    """
    logs = []
    engine_app = d.get_engine_app()
    client = EngineDeployClient(engine_app)
    # NOTE: 当前暂不包含“准备阶段”和“检测部署结果”这两个步骤的日志，将在未来版本添加
    if d.build_process_id:
        logs.extend([polish_line(obj['line']) for obj in client.list_build_proc_logs(d.build_process_id)])
    if d.pre_release_id:
        logs.extend([polish_line(obj['line']) for obj in client.list_command_logs(d.pre_release_id)])
    return "".join(logs) + "\n" + (d.err_detail or '')


class EngineDeployClient:
    """A high level client for engine, provides functions related with deployments"""

    def __init__(self, engine_app):
        self.engine_app = engine_app

    @cached_property
    def wl_app(self) -> WlApp:
        """Make 'wl_app' a property so tests using current class won't panic when
        initializing because not data can be found in workloads module.
        """
        return self.engine_app.to_wl_obj()

    def create_build(self, image: str, extra_envs: Dict[str, str], procfile: Dict[str, str]) -> str:
        """Create the **fake** build for Image Type App"""
        build = Build.objects.create(
            app=self.wl_app,
            env_variables=extra_envs,
            procfile=procfile,
            image=image,
            artifact_type=ArtifactType.NONE,
        )
        return str(build.uuid)

    def list_command_logs(self, command_id: str) -> List[LogLine]:
        """List all logs of command"""
        command = self.wl_app.command_set.get(pk=command_id)
        return [{'stream': line.stream, 'line': line.line, 'created': line.created} for line in command.lines]

    def list_build_proc_logs(self, build_process_id: str) -> List[LogLine]:
        """Get current status of build process"""
        build_proc = BuildProcess.objects.get(pk=build_process_id)

        lines: List[LogLine] = []
        for line in build_proc.output_stream.lines.all().order_by('created'):
            lines.append({'stream': line.stream, 'line': line.line, 'created': line.created})
        return lines

    def upsert_image_credentials(self, registry: str, username: str, password: str):
        """Update an engine app's image credentials, which will be used to pull image."""
        AppImageCredential.objects.update_or_create(
            app=self.wl_app,
            registry=registry,
            defaults={"username": username, "password": password},
        )
