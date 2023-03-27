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
"""Releasing process of an application deployment
"""
import logging
import typing
from typing import Optional

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, CallbackStatus, TaskPoller
from django.utils.translation import gettext as _
from pydantic import ValidationError as PyDanticValidationError

from paasng.engine.configurations.building import get_processes_by_build
from paasng.engine.configurations.config_var import get_env_variables
from paasng.engine.configurations.image import update_image_runtime_config
from paasng.engine.configurations.ingress import AppDefaultDomains, AppDefaultSubpaths
from paasng.engine.constants import JobStatus, ReleaseStatus
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.phases import DeployPhaseTypes
from paasng.engine.models.processes import ProcessManager
from paasng.engine.processes.wait import AbortedDetails, wait_for_release
from paasng.engine.signals import on_release_created
from paasng.engine.workflow import DeployStep
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class ApplicationReleaseMgr(DeployStep):
    """The release manager"""

    PHASE_TYPE = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        with self.procedure(_('更新进程配置')):
            # only sync `command` field in release
            processes = [{"name": name, "command": command} for name, command in self.deployment.procfile.items()]
            ProcessManager(self.engine_app).sync_processes_specs(processes)

        with self.procedure(_('更新应用配置')):
            update_image_runtime_config(
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


class ReleaseResultHandler(CallbackHandler):
    """Result handler for `wait_for_release`"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        is_interrupted, error_detail = self.get_error_detail(result)
        # Transform release_status
        if is_interrupted:
            status = ReleaseStatus.INTERRUPTED
        elif error_detail:
            status = ReleaseStatus.FAILED
        else:
            status = ReleaseStatus.SUCCESSFUL

        deployment_id = poller.params['extra_params']['deployment_id']
        self.finish_release(str(deployment_id), status, error_detail)

    def finish_release(self, deployment_id: str, status: ReleaseStatus, error_detail: str):
        """Finish the release"""
        mgr = ApplicationReleaseMgr.from_deployment_id(deployment_id)
        mgr.callback_release(status.to_job_status(), error_detail)

    def get_error_detail(self, result: CallbackResult) -> typing.Tuple[bool, str]:
        """Get detailed error message. if error message was empty, release was considered succeeded

        :returns: (is_interrupted, error_msg)
        """
        if result.status == CallbackStatus.TIMEOUT:
            return False, "Timeout: polling release's status taking too long to complete"

        if result.status == CallbackStatus.NORMAL:
            aborted_details = self.get_aborted_details(result)
            if not (aborted_details and aborted_details.aborted):
                return False, ''

            assert aborted_details.policy is not None, 'policy must not be None'  # Make type checker happy
            reason = aborted_details.policy.reason
            return aborted_details.policy.is_interrupted, f'Release aborted, reason: {reason}'

        return False, 'Release failed, internal error'

    def get_aborted_details(self, result: CallbackResult) -> Optional[AbortedDetails]:
        """If current release was aborted, return detailed info"""
        try:
            details = AbortedDetails.parse_obj(result.data)
        except PyDanticValidationError:
            return None
        return details


def create_release(env: ModuleEnvironment, build_id: str, deployment: Optional[Deployment] = None) -> str:
    """Create a new release for the given environment. If the optional deployment
    object is given, will start a async waiting procedure which waits for the release
    to be finished.

    :param env: The environment to create the release for.
    :param build_id: The ID of the finished build object.
    :param deployment: if not given, will try using the latest succeed deployment for getting desc env vars
    :return: The ID of the created release object.
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
        procfile = get_processes_by_build(build_id)
        deployment_id = None

    extra_envs = get_env_variables(env, deployment=deployment)

    # Create the release and start the background task to wait for the release if needed
    release = EngineDeployClient(env.get_engine_app()).create_release(build_id, deployment_id, extra_envs, procfile)
    if deployment_id:
        wait_for_release(
            env=env,
            release_version=release.version,
            result_handler=ReleaseResultHandler,
            extra_params={"deployment_id": deployment_id},
        )
    return str(release.uuid)
