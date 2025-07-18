# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Releasing process of an application deployment"""

import logging
from typing import Dict, Optional, Tuple

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, CallbackStatus, TaskPoller
from pydantic import ValidationError as PyDanticValidationError

from paas_wl.bk_app.applications.models.build import Build
from paas_wl.bk_app.applications.models.release import Release
from paas_wl.bk_app.deploy.actions.deploy import DeployAction
from paas_wl.bk_app.processes.processes import ProcessManager
from paas_wl.infras.resources.base.exceptions import KubeException
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.configurations.image import update_image_runtime_config
from paasng.platform.engine.configurations.ingress import AppDefaultDomains, AppDefaultSubpaths
from paasng.platform.engine.constants import JobStatus, ReleaseStatus
from paasng.platform.engine.deploy.bg_wait.base import AbortedDetails
from paasng.platform.engine.deploy.bg_wait.wait_deployment import wait_for_release
from paasng.platform.engine.exceptions import StepNotInPresetListError
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.signals import on_release_created
from paasng.platform.engine.utils.query import DeploymentGetter
from paasng.platform.engine.workflow import DeployStep

logger = logging.getLogger(__name__)


class ApplicationReleaseMgr(DeployStep):
    """Application Release Step, will schedule the Deployment/Ingress and so on by python k8s client.
    Python k8s client will call k8s api at platform cluster.
    """

    phase_type = DeployPhaseTypes.RELEASE

    @DeployStep.procedures
    def start(self):
        if self.deployment.has_requested_int:
            self.state_mgr.finish(JobStatus.INTERRUPTED, "app release interrupted")
            return

        with self.procedure("更新进程配置"):
            # Turn the processes into the corresponding type in paas_wl module
            procs = self.deployment.get_processes()
            proc_mgr = ProcessManager(self.engine_app.env)
            proc_mgr.sync_processes_specs(procs)

        with self.procedure("更新应用配置"):
            update_image_runtime_config(deployment=self.deployment)

        with self.procedure("部署应用"):
            release_id = release_by_engine(
                self.module_environment, str(self.deployment.build_id), deployment=self.deployment
            )
            self.sync_entrance_configs()
            # Emit a signal to notify that the ModuleEnvironment is going to release
            on_release_created.send(env=self.module_environment, sender=self.deployment)

        # 这里只是轮询开始，具体状态更新需要放到轮询组件中完成
        self.state_mgr.update(release_id=release_id)
        try:
            step_obj = self.phase.get_step_by_name(name="检测部署结果")
            step_obj.mark_and_write_to_stream(self.stream, JobStatus.PENDING, extra_info=dict(release_id=release_id))
        except StepNotInPresetListError:
            logger.debug("Step not found or duplicated, name: %s", "检测部署结果")

    def sync_entrance_configs(self):
        """Sync app's default subdomains/subpaths with engine backend"""
        AppDefaultDomains(self.module_environment).sync()
        AppDefaultSubpaths(self.module_environment).sync()

    def callback_release(self, status: JobStatus, error_detail: str):
        """Callback function for a finished release

        :param status: status of release
        :param error_detail: detailed error message when release has failed
        """
        try:
            step_obj = self.phase.get_step_by_name(name="检测部署结果")
            step_obj.mark_and_write_to_stream(self.stream, status)
        except StepNotInPresetListError:
            logger.debug("Step not found or duplicated, name: %s", "检测部署结果")
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

        deployment_id = poller.params["extra_params"]["deployment_id"]
        self.finish_release(str(deployment_id), status, error_detail)

    def finish_release(self, deployment_id: str, status: ReleaseStatus, error_detail: str):
        """Finish the release"""
        mgr = ApplicationReleaseMgr.from_deployment_id(deployment_id)
        mgr.callback_release(status.to_job_status(), error_detail)

    def get_error_detail(self, result: CallbackResult) -> Tuple[bool, str]:
        """Get detailed error message. if error message was empty, release was considered succeeded

        :returns: (is_interrupted, error_msg)
        """
        if result.status == CallbackStatus.TIMEOUT:
            return False, "Timeout: polling release's status taking too long to complete"

        if result.status == CallbackStatus.NORMAL:
            aborted_details = self.get_aborted_details(result)
            if not (aborted_details and aborted_details.aborted):
                return False, ""

            assert aborted_details.policy is not None, "policy must not be None"  # Make type checker happy
            reason = aborted_details.policy.reason
            return aborted_details.policy.is_interrupted, f"Release aborted, reason: {reason}"

        return False, "Release failed, internal error"

    def get_aborted_details(self, result: CallbackResult) -> Optional[AbortedDetails]:
        """If current release was aborted, return detailed info"""
        try:
            details = AbortedDetails.parse_obj(result.data)
        except PyDanticValidationError:
            return None
        return details


def release_by_engine(env: ModuleEnvironment, build_id: str, deployment: Optional[Deployment] = None) -> str:
    """Create a new release for the given environment.

    If the optional deployment object is given, will start an async waiting procedure
    which waits for the release to be finished.

    :param env: The environment to create the release for.
    :param build_id: The ID of the finished build object.
    :param deployment: if not given, will try using the latest succeed deployment.
    :return: The ID of the created release object.
    :raises ValueError: if no deployment object can be found
    """
    # Only start the async waiting if the deployment parameter is given
    start_async_waiting = deployment is not None

    # Try to get the deployment object if it's not given
    # 1. Get the deployment object by the `build_id`
    if not deployment:
        try:
            deployment = Deployment.objects.filter(build_id=build_id).latest_succeeded()
        except Deployment.DoesNotExist:
            logger.warning("Cannot find any succeeded deployment for build %s", build_id)
    # 2. Get the latest succeeded deployment if still not found
    if not deployment:
        deployment = DeploymentGetter(env).get_latest_succeeded()

    if not deployment:
        raise ValueError("No deployment object can be found")

    # Create the release and start the background task to wait for the release if needed
    extra_envs = get_env_variables(env)
    release = release_to_k8s(env, build_id, extra_envs, deployment.get_procfile())
    if start_async_waiting:
        wait_for_release(
            env=env,
            release_version=release.version,
            result_handler=ReleaseResultHandler,
            extra_params={"deployment_id": str(deployment.id)},
        )
    return str(release.uuid)


def release_to_k8s(
    env: ModuleEnvironment, build_id: str, extra_envs: Dict[str, str], procfile: Dict[str, str]
) -> Release:
    """Create a new release object, and perform DeployAction

    :param env: The environment to create the release for.
    :param build_id: The ID of the finished build object.
    :param extra_envs: env vars of current environment
    :param procfile: Procfile to run the process

    :return: The created release object.
    """
    build = Build.objects.get(pk=build_id)
    release = env.wl_app.release_set.new(
        owner=build.owner,
        build=build,
        procfile=procfile,
    )

    try:
        DeployAction(env=env, release=release, extra_envs=extra_envs).perform()
    except KubeException:  # noqa: TRY302
        # TODO: Wrap exception and re-raise
        raise
    return release
