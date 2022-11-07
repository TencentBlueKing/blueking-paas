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
"""Releasing process of an application deployment
"""
import logging
from typing import Optional

from django.utils.translation import gettext as _

from paasng.engine.constants import JobStatus
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.infras import AppDefaultDomains, AppDefaultSubpaths, DeployStep, get_env_variables
from paasng.engine.deploy.preparations import get_processes_by_build, update_engine_app_config
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.phases import DeployPhaseTypes
from paasng.engine.models.processes import ProcessManager
from paasng.engine.signals import on_release_created
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class ApplicationReleaseMgr(DeployStep):
    """The release manager"""

    PHASE_TYPE = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        with self.procedure(_('更新进程配置')):
            processes = [{"name": name, "command": command} for name, command in self.deployment.procfile.items()]
            ProcessManager(self.engine_app, self.engine_client.ctl_client).sync_processes_specs(processes)

        with self.procedure(_('更新应用配置')):
            update_engine_app_config(
                self.engine_app,
                self.deployment.version_info,
                image_pull_policy=self.deployment.advanced_options.image_pull_policy,
            )

        with self.procedure(_('部署应用')):
            release_id = create_release(
                self.module_environment, str(self.deployment.build_id), deployment=self.deployment
            )
            self.sync_entrance_configs()
            # Emit a signal to notify that the ModuleEnvironment is going to release
            on_release_created.send(env=self.module_environment, sender=self.deployment)

        # 这里只是轮询开始，具体状态更新需要放到轮询组件中完成
        self.state_mgr.update(release_id=release_id)
        step_obj = self.phase.get_step_by_name(name=_("检测部署结果"))
        step_obj.mark_and_write_to_steam(self.stream, JobStatus.PENDING, extra_info=dict(release_id=release_id))

    def sync_entrance_configs(self):
        """Sync app's default subdomains/subpaths with engine backend"""
        AppDefaultDomains(self.module_environment).sync()
        AppDefaultSubpaths(self.module_environment).sync()

    def callback_release(self, status: JobStatus, error_detail: str):
        """Callback function for a finished release

        :param status: status of release
        :param error_detail: detailed error message when release has failed
        """
        if status == JobStatus.SUCCESSFUL:
            self.deployment.app_environment.is_offlined = False
            self.deployment.app_environment.save()

        step_obj = self.phase.get_step_by_name(name=_("检测部署结果"))
        step_obj.mark_and_write_to_steam(self.stream, status)
        self.state_mgr.update(release_status=status)
        self.state_mgr.finish(status, err_detail=error_detail, write_to_stream=True)


def create_release(env: ModuleEnvironment, build_id: str, deployment: Optional[Deployment] = None) -> str:
    """Create a new release by calling enging's API

    :param deployment: if not given, will try using the latest succeed deployment for getting desc env vars
    """
    if not deployment:
        try:
            deployment = env.deployments.latest_succeeded()
        except Deployment.DoesNotExist:
            pass

    deployment_id: Optional[str]
    if deployment:
        procfile = deployment.procfile
        deployment_id = str(deployment.id)
    else:
        # NOTE: 更新环境变量时的 Pod 滚动时没有 deployment, 需要从 engine 中查询 procfile
        # TODO: 直接使用上一次成功的 deployment 中记录的 procfile
        procfile = get_processes_by_build(engine_app=env.engine_app, build_id=build_id)
        deployment_id = None

    extra_envs = get_env_variables(env, deployment=deployment)
    return EngineDeployClient(env.get_engine_app()).create_release(build_id, deployment_id, extra_envs, procfile)
