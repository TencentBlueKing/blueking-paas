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
from typing import TYPE_CHECKING, Dict, List, Optional, TypedDict

from django.conf import settings
from django.utils.functional import cached_property

from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.models.build import Build, BuildProcess
from paas_wl.platform.applications.models.misc import OutputStream
from paas_wl.platform.applications.models.release import Release
from paas_wl.release_controller.builder import tasks as builder_task
from paas_wl.resources import tasks as scheduler_tasks
from paas_wl.resources.actions.deploy import AppDeploy
from paas_wl.resources.base.exceptions import KubeException
from paas_wl.utils.constants import CommandStatus, CommandType
from paas_wl.workloads.images.models import AppImageCredential
from paasng.engine.configurations.building import SlugbuilderInfo
from paasng.engine.constants import JobStatus
from paasng.engine.models.deployment import Deployment

if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.models import VersionInfo


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

    def start_build_process(
        self,
        version: 'VersionInfo',
        stream_channel_id: str,
        source_tar_path: str,
        procfile: dict,
        extra_envs: Dict[str, str],
    ) -> str:
        """Start a new build process"""
        # get slugbuilder and buildpacks from engine_app
        build_info = SlugbuilderInfo.from_engine_app(self.engine_app)
        # 注入构建环境所需环境变量
        extra_envs = {**extra_envs, **build_info.environments}

        # Use the default image when it's None, which means no images are bound to the app
        image = build_info.build_image or settings.DEFAULT_SLUGBUILDER_IMAGE
        # Create the Build object and start a background build task
        build_process = BuildProcess.objects.create(
            # TODO: Set the correct owner value
            # owner='',
            app=self.wl_app,
            source_tar_path=source_tar_path,
            revision=version.revision,
            branch=version.version_name,
            output_stream=OutputStream.objects.create(),
            image=image,
            buildpacks=build_info.buildpacks_info or [],
        )
        builder_task.start_build_process.delay(
            build_process.uuid,
            stream_channel_id=stream_channel_id,
            metadata={
                'procfile': procfile,
                'extra_envs': extra_envs or {},
                'image': image,
                'buildpacks': build_process.buildpacks_as_build_env(),
            },
        )
        return str(build_process.uuid)

    def run_command(
        self, build_id: str, command: str, stream_channel_id: str, operator: str, type_: str, extra_envs: Dict
    ) -> str:
        """run a command in a built slug."""
        build = self.wl_app.build_set.get(pk=build_id)
        cmd_obj = self.wl_app.command_set.new(
            type_=CommandType(type_),
            command=command,
            build=build,
            operator=operator,
        )

        scheduler_tasks.run_command.delay(
            cmd_obj.uuid, stream_channel_id=stream_channel_id, extra_envs=extra_envs or {}
        )
        return str(cmd_obj.uuid)

    def get_command_status(self, command_id: str) -> JobStatus:
        """Get current status of command"""
        command = self.wl_app.command_set.get(pk=command_id)

        # TODO: Write a function which turn CommandStatus into JobStatus
        if command.status == CommandStatus.SCHEDULED.value:
            return JobStatus(CommandStatus.PENDING.value)
        return JobStatus(command.status)

    def list_command_logs(self, command_id: str) -> List[LogLine]:
        """List all logs of command"""
        command = self.wl_app.command_set.get(pk=command_id)
        return [{'stream': line.stream, 'line': line.line, 'created': line.created} for line in command.lines]

    def create_release(
        self, build_id: str, deployment_id: Optional[str], extra_envs: Dict[str, str], procfile: Dict[str, str]
    ) -> Release:
        """Create a new release

        :return: The created release object.
        """
        build = Build.objects.get(pk=build_id)
        release = build.app.release_set.new(
            # TODO: Set the correct owner value
            owner='',
            build=build,
            procfile=procfile,
        )

        try:
            wl_app = release.app
            AppDeploy(app=wl_app, release=release, extra_envs=extra_envs).perform()
        except KubeException:
            # TODO: Wrap exception and re-raise
            raise
        return release

    def create_build(self, extra_envs: Dict[str, str], procfile: Dict[str, str]) -> str:
        """Create the **fake** build for Image Type App"""
        build = Build.objects.create(
            app=self.wl_app,
            env_variables=extra_envs,
            procfile=procfile,
        )
        return str(build.uuid)

    def get_build_process(self, build_process_id: str) -> BuildProcess:
        """Get current status of build process"""
        return BuildProcess.objects.get(pk=build_process_id)

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
