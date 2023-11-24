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
from typing import Dict

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, PollingResult, PollingStatus, TaskPoller
from django.utils.translation import gettext as _

from paas_wl.utils.constants import CommandStatus, CommandType
from paas_wl.workloads.release_controller.hooks.entities import CommandTemplate
from paas_wl.workloads.release_controller.hooks.models import Command
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.configurations.image import update_image_runtime_config
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.base import DeployPoller
from paasng.platform.engine.deploy.bg_command.tasks import exec_command
from paasng.platform.engine.deploy.release.legacy import ApplicationReleaseMgr
from paasng.platform.engine.exceptions import StepNotInPresetListError
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.signals import pre_phase_start
from paasng.platform.engine.utils.output import Style
from paasng.platform.engine.workflow import DeploymentCoordinator, DeploymentStateMgr, DeployStep
from paasng.platform.modules.constants import DeployHookType


class ApplicationPreReleaseExecutor(DeployStep):
    PHASE_TYPE = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        pre_phase_start.send(self, phase=DeployPhaseTypes.RELEASE)

        hook = self.deployment.get_deploy_hooks().get_hook(type_=DeployHookType.PRE_RELEASE_HOOK)
        if hook is None or not (hook.enabled and hook.command):
            self.stream.write_message(
                Style.Warning(_("The Pre-release command is not configured, skip the Pre-release phase."))
            )
            # Start release process
            return ApplicationReleaseMgr.from_deployment_id(self.deployment.id).start()

        with self.procedure("更新应用配置"):
            update_image_runtime_config(deployment=self.deployment)

        with self.procedure("初始化指令执行环境"):
            extra_envs = get_env_variables(self.engine_app.env, deployment=self.deployment)
            command_id = exec_command(
                self.engine_app.env,
                command_template=CommandTemplate(
                    build_id=str(self.deployment.build_id),
                    command=hook.command,
                    type=CommandType(hook.type),
                ),
                operator=str(self.deployment.operator),
                stream_channel_id=str(self.deployment.id),
                extra_envs=extra_envs,
            )

        self.state_mgr.update(pre_release_id=command_id)
        self.mark_step_start()
        params = {"command_id": command_id, "deployment_id": str(self.deployment.id)}
        CommandPoller.start(params, PreReleaseHookCompleteHandler)

    def on_puller_complete(self, result: Dict):
        """Callback for a finished pre-release command"""
        try:
            status = JobStatus(result["command_status"])
        except KeyError:
            self.state_mgr.finish(JobStatus.FAILED, "An unexpected error occurred while running pre-release hook")
            return

        self.state_mgr.update(pre_release_status=status)
        self.mark_step_finish(status=status)
        if status == JobStatus.FAILED:
            self.state_mgr.finish(JobStatus.FAILED, "Pre-Release-Hook failed, please check logs for more details")
        elif status == JobStatus.INTERRUPTED:
            self.state_mgr.finish(JobStatus.INTERRUPTED, "Pre-Release-Hook interrupted")
        else:
            # Start release process
            ApplicationReleaseMgr.from_deployment_id(self.deployment.id).start()

    def mark_step_start(self):
        try:
            step = self.phase.get_step_by_name("执行部署前置命令")
        except StepNotInPresetListError:
            return
        step.mark_procedure_status(JobStatus.PENDING)

    def mark_step_finish(self, status: JobStatus):
        try:
            step = self.phase.get_step_by_name("执行部署前置命令")
        except StepNotInPresetListError:
            return
        step.mark_and_write_to_stream(stream=self.stream, status=status)


class CommandPoller(DeployPoller):
    """Poller for querying the status of a user command
    Finish when the command in engine side was completed
    """

    overall_timeout_seconds = 30 * 60

    def query(self) -> PollingResult:
        deployment = Deployment.objects.get(pk=self.params["deployment_id"])

        command = Command.objects.get(pk=self.params["command_id"])
        command_status = CommandStatus(command.status)

        coordinator = DeploymentCoordinator(deployment.app_environment)
        # 若判断任务状态超时，则认为任务失败，否则更新上报状态时间
        if coordinator.status_polling_timeout:
            command_status = CommandStatus.FAILED
        else:
            coordinator.update_polling_time()

        if command_status in CommandStatus.get_finished_states():
            poller_status = PollingStatus.DONE
        else:
            poller_status = PollingStatus.DOING

        result = {"command_status": command_status.to_job_status()}
        return PollingResult(status=poller_status, data=result)


class PreReleaseHookCompleteHandler(CallbackHandler):
    """Result handler for a finished pre-release-hook"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        deployment_id = poller.params["deployment_id"]
        state_mgr = DeploymentStateMgr.from_deployment_id(
            deployment_id=deployment_id, phase_type=DeployPhaseTypes.RELEASE
        )

        if result.is_exception:
            state_mgr.finish(JobStatus.FAILED, "pre-release-hook failed")
        else:
            ApplicationPreReleaseExecutor.from_deployment_id(deployment_id).on_puller_complete(result.data)
