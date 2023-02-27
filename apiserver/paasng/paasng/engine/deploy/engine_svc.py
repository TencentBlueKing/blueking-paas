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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from django.conf import settings

from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.platform.applications.models.misc import OutputStream
from paas_wl.release_controller.builder import tasks as builder_task
from paasng.engine.controller.client import ControllerClient
from paasng.engine.controller.shortcuts import make_internal_client
from paasng.engine.helpers import SlugbuilderInfo

if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.models import VersionInfo


class EngineDeployClient:
    """A high level client for engine"""

    def __init__(self, engine_app, controller_client: Optional[ControllerClient] = None):
        self.engine_app = engine_app
        self.ctl_client = controller_client or make_internal_client()

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

        # Create the Build object and start a background build task
        build_process = BuildProcess.objects.create(
            # TODO: Set the correct owner value
            # owner=None,
            app=self.engine_app.to_wl_obj(),
            source_tar_path=source_tar_path,
            revision=version.revision,
            branch=version.version_name,
            output_stream=OutputStream.objects.create(),
            image=build_info.build_image or settings.DEFAULT_SLUGBUILDER_IMAGE,
            buildpacks=build_info.buildpacks_info or [],
        )
        builder_task.start_build_process.delay(
            build_process.uuid,
            stream_channel_id=stream_channel_id,
            metadata={
                'procfile': procfile,
                'extra_envs': extra_envs or {},
                'image': build_info.build_image,
                'buildpacks': build_process.buildpacks_as_build_env(),
            },
        )
        return str(build_process.uuid)

    def run_command(
        self, build_id: str, command: str, stream_channel_id: str, operator: str, type_: str, extra_envs: Dict
    ) -> str:
        """run a command in a built slug."""
        resp = self.ctl_client.app__run_command(
            region=self.engine_app.region,
            app_name=self.engine_app.name,
            build_id=build_id,
            command=command,
            stream_channel_id=stream_channel_id,
            operator=operator,
            type_=type_,
            extra_envs=extra_envs,
        )
        command_id = resp.get("uuid")
        return command_id

    def get_command_status(self, command_id: str) -> Dict[str, Any]:
        """Get current status of command"""
        resp = self.ctl_client.command__retrieve(
            region=self.engine_app.region, app_name=self.engine_app.name, command_id=command_id
        )
        return resp

    def update_config(self, runtime: Dict[str, Any]):
        """Update engine-app's config"""
        payload = {"runtime": runtime}

        return self.ctl_client.update_app_config(
            app_name=self.engine_app.name,
            region=self.engine_app.region,
            payload=payload,
        )

    def create_release(
        self, build_id: str, deployment_id: Optional[str], extra_envs: Dict[str, str], procfile: Dict[str, str]
    ) -> str:
        """Create a new release"""
        resp = self.ctl_client.app__release(
            app_name=self.engine_app.name,
            region=self.engine_app.region,
            build_id=build_id,
            deployment_id=deployment_id,
            extra_envs=extra_envs,
            procfile=procfile,
        )
        return resp['uuid']

    def get_release(self, release_id: str) -> dict:
        """Get the release object by id"""
        return self.ctl_client.get_app_release(
            region=self.engine_app.region, app_name=self.engine_app.name, release_id=release_id
        )

    def create_build(self, extra_envs: Dict[str, str], procfile: Dict[str, str]) -> str:
        """Create the **fake** build for Image Type App"""
        resp = self.ctl_client.create_build(
            region=self.engine_app.region,
            app_name=self.engine_app.name,
            procfile=procfile,
            env_variables=extra_envs,
        )
        return resp["uuid"]

    def get_build(self, build_id: str) -> dict:
        """Get the build object by id"""
        return self.ctl_client.get_app_build(
            region=self.engine_app.region, app_name=self.engine_app.name, build_id=build_id
        )

    def get_build_process_status(self, build_process_id: str) -> Dict[str, Any]:
        """Get current status of build process"""
        resp = self.ctl_client.read_build_process_result(
            app_name=self.engine_app.name, region=self.engine_app.region, build_process_id=build_process_id
        )
        return resp

    def update_domains(self, domains: List[Dict]):
        """Update an engine app's domains"""
        self.ctl_client.app_domains__update(
            region=self.engine_app.region, app_name=self.engine_app.name, domains=domains
        )

    def update_subpaths(self, subpaths: List[Dict]):
        """Update an engine app's subpaths"""
        self.ctl_client.update_app_subpaths(
            region=self.engine_app.region, app_name=self.engine_app.name, subpaths=subpaths
        )

    def get_metadata(self) -> Dict[str, Any]:
        """Get an engine app's metadata"""
        config = self.ctl_client.retrieve_app_config(region=self.engine_app.region, app_name=self.engine_app.name)
        return config['metadata'] or {}

    def update_metadata(self, metadata_part: Dict[str, Union[str, bool]]):
        """Update an engine app's metadata, works like python's dict.update()

        :param metadata_part: An dict object which will be merged into app's metadata
        """
        self.ctl_client.update_app_metadata(
            region=self.engine_app.region, app_name=self.engine_app.name, payload={'metadata': metadata_part}
        )

    def upsert_image_credentials(self, registry: str, username: str, password: str):
        """Update an engine app's image credentials, which will be used to pull image."""
        self.ctl_client.upsert_image_credentials(
            region=self.engine_app.region,
            app_name=self.engine_app.name,
            credentials={"registry": registry, "username": username, "password": password},
        )

    def sync_proc_ingresses(self):
        """Sync ingresses configs with engine"""
        self.ctl_client.app_proc_ingress_actions__sync(region=self.engine_app.region, app_name=self.engine_app.name)
