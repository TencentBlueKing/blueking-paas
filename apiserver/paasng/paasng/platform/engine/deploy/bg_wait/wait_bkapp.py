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
"""Wait for BkApp's reconciliation cycle to be stable"""
import datetime
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from blue_krill.async_utils.poll_task import (
    CallbackHandler,
    CallbackResult,
    PollingMetadata,
    PollingResult,
    PollingStatus,
    TaskPoller,
)
from django.utils import timezone
from pydantic import ValidationError as PyDanticValidationError

from paas_wl.bk_app.cnative.specs.constants import CNATIVE_DEPLOY_STATUS_POLLING_FAILURE_LIMITS, DeployStatus
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy
from paas_wl.bk_app.cnative.specs.resource import ModelResState, MresConditionParser, get_mres_from_cluster
from paas_wl.bk_app.cnative.specs.signals import post_cnative_env_deploy
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.bg_wait.base import AbortedDetails, AbortedDetailsPolicy
from paasng.platform.engine.exceptions import StepNotInPresetListError
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.phases import DeployPhaseTypes
from paasng.platform.engine.workflow.flow import DeploymentStateMgr

logger = logging.getLogger(__name__)


class AbortPolicy(ABC):
    """Base class for wait policy"""

    @abstractmethod
    def get_reason(self) -> str:
        """Reason of abortion"""

    @property
    def is_interrupted(self) -> bool:
        """If the wait procedure was aborted by current policy, whether is was considered as an interruption
        or a regular failure.
        """
        return False

    @abstractmethod
    def evaluate(self, already_waited: float, extra_params: Dict) -> bool:
        """Determine if current wait procedure should be aborted

        :param already_waited: how long since current procedure has been started, in seconds
        :param extra_params: extra params of current procedure
        """


class UserInterruptedPolicy(AbortPolicy):
    """Abort procedure when user requested an interruption"""

    def get_reason(self) -> str:
        return 'User interrupted release'

    @property
    def is_interrupted(self) -> bool:
        return True

    def evaluate(self, already_waited: float, params: Dict) -> bool:
        deployment_id = params.get('deployment_id')
        if not deployment_id:
            logger.warning('Deployment was not provided for UserInterruptedPolicy, will not proceed.')
            return False

        try:
            deployment = Deployment.objects.get(pk=deployment_id)
        except Deployment.DoesNotExist:
            logger.warning('Deployment not exists for UserInterruptedPolicy, will not proceed.')
            return False
        return bool(deployment.release_int_requested_at)


class WaitProcedurePoller(TaskPoller):
    """Base class of process waiting procedure

    `params` schema:
    :param module_env_id: id of ModuleEnvironment object
    """

    # over 15 min considered as timeout
    overall_timeout_seconds = 15 * 60
    # Abort policies were extra rules which were used to break current polling procedure
    abort_policies: List[AbortPolicy] = []

    def __init__(self, params: Dict, metadata: PollingMetadata):
        super().__init__(params, metadata)
        self.env = ModuleEnvironment.objects.get(pk=self.params['env_id'])

    def query(self) -> PollingResult:
        already_waited = time.time() - self.metadata.query_started_at
        logger.info(f'wait procedure started {already_waited} seconds, env: {self.env}')
        # Check all abort policies
        for policy in self.abort_policies:
            if policy.evaluate(already_waited, self.params):
                policy_name = policy.__class__.__name__
                logger.info(f'AbortPolicy: {policy_name} evaluated, got positive result, abort current procedure')
                return PollingResult(
                    PollingStatus.DONE,
                    data=AbortedDetails(
                        aborted=True,
                        policy=AbortedDetailsPolicy(
                            reason=policy.get_reason(),
                            name=policy_name,
                            is_interrupted=policy.is_interrupted,
                        ),
                    ).dict(),
                )

        polling_result = self.get_status()
        if polling_result.status != PollingStatus.DOING:
            # reserve original data in `extra_data` field
            polling_result.data = AbortedDetails(aborted=False, extra_data=polling_result.data).dict()
        return polling_result

    def get_status(self) -> PollingResult:
        raise NotImplementedError()


class WaitAppModelReady(WaitProcedurePoller):
    """A task poller to query status for fresh AppModelDeploy objects

    It takes below params:

    `params` schema:
    :param module_env_id: id of ModuleEnvironment object
    :param deploy_id: int, ID of AppModelDeploy object
    :param deployment_id: Optional[uuid]: ID of Deployment object
    """

    # over 15 min considered as timeout
    overall_timeout_seconds = 15 * 60
    # Abort policies were extra rules which were used to break current polling procedure
    abort_policies: List[AbortPolicy] = [UserInterruptedPolicy()]

    def get_status(self) -> PollingResult:
        dp = AppModelDeploy.objects.get(id=self.params['deploy_id'])
        mres = get_mres_from_cluster(
            ModuleEnvironment.objects.get(
                application_id=dp.application_id, module_id=dp.module_id, environment=dp.environment_name
            )
        )

        if not mres:
            return PollingResult.doing()

        state = MresConditionParser(mres).detect_state()
        if state.status == DeployStatus.READY:
            return PollingResult.done(data={'state': state, 'last_update': mres.status.lastUpdate})

        elif state.status == DeployStatus.ERROR:
            polling_failure_count = 1
            if self.metadata.last_polling_data and 'polling_failure_count' in self.metadata.last_polling_data:
                polling_failure_count = self.metadata.last_polling_data['polling_failure_count'] + 1

            # When deploying bkapp, temporary failures may occur but will quickly resume
            # e.g. Deployment does not have minimum availability
            # When polling the deployment result, we should allow such cases and retry.
            # Only when the consecutive polling failures count exceeds the limit,
            # then current deployment should be considered as failed.
            if polling_failure_count > CNATIVE_DEPLOY_STATUS_POLLING_FAILURE_LIMITS:
                return PollingResult.done(data={'state': state, 'last_update': mres.status.lastUpdate})

            return PollingResult.doing(data={'polling_failure_count': polling_failure_count})

        elif state.status == DeployStatus.PROGRESSING:
            # Also update status when it's progressing
            update_status(dp, state, last_transition_time=mres.status.lastUpdate)

        # Still pending, do another query later
        return PollingResult.doing()


class DeployStatusHandler(CallbackHandler):
    """Result handler for AppModelDeployStatusPoller"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        dp = AppModelDeploy.objects.get(id=poller.params['deploy_id'])

        is_interrupted, err_message, extra_data = self.parse_result(result)
        if result.is_exception or (not is_interrupted and err_message):
            logger.warning('Error polling AppModelDeploy status, result: %s', result)
            state = ModelResState(DeployStatus.ERROR, 'internal', err_message)
            update_status(dp, state)
        elif is_interrupted:
            logger.warning('polling AppModelDeploy is interrupted')
            state = ModelResState(DeployStatus.UNKNOWN, 'interrupted', err_message)
            update_status(dp, state)
        else:
            logger.info('Update AppModelDeploy status with data: %s', result.data)
            update_status(dp, extra_data['state'], last_transition_time=extra_data['last_update'])

        dp.refresh_from_db()
        # 需要更新 deploy step 的状态
        deployment_id = poller.params.get('deployment_id')
        if deployment_id is not None:
            state_mgr = DeploymentStateMgr.from_deployment_id(
                deployment_id=deployment_id, phase_type=DeployPhaseTypes.RELEASE
            )
            job_status = deploy_status_to_job_status(dp.status) if not is_interrupted else JobStatus.INTERRUPTED
            try:
                step_obj = state_mgr.phase.get_step_by_name(name="检测部署结果")
                step_obj.mark_and_write_to_stream(state_mgr.stream, job_status)
            except StepNotInPresetListError:
                logger.debug("Step not found or duplicated, name: %s", "检测部署结果")
            state_mgr.update(release_status=job_status)
            state_mgr.finish(job_status, err_detail=dp.message or '', write_to_stream=True)

        # 在部署流程结束后，发送信号触发操作审计等后续步骤(不支持创建监控告警规则)
        post_cnative_env_deploy.send(dp.environment, deploy=dp)

    def parse_result(self, result: CallbackResult) -> Tuple[bool, str, Dict]:
        """Get detailed error message. if error message was empty, release was considered succeeded

        :returns: (is_interrupted, error_msg, extra_data)
        """
        if result.is_exception:
            return False, "error polling deploy status", result.data

        aborted_details = self.get_aborted_details(result)
        if not aborted_details:
            return False, "invalid polling result", result.data

        if aborted_details.aborted:
            assert aborted_details.policy is not None, 'policy must not be None'  # Make type checker happy
            return (
                aborted_details.policy.is_interrupted,
                aborted_details.policy.reason,
                aborted_details.extra_data or {},
            )

        # if error message was empty, release was considered succeeded
        return False, "", aborted_details.extra_data or {}

    @staticmethod
    def get_aborted_details(result: CallbackResult) -> Optional[AbortedDetails]:
        """If current release was aborted, return detailed info"""
        try:
            details = AbortedDetails.parse_obj(result.data)
        except PyDanticValidationError:
            return None
        return details


def update_status(dp: AppModelDeploy, state: ModelResState, last_transition_time: Optional[datetime.datetime] = None):
    """Update deployment status, `last_transition_time` will always be updated

    :param dp: The AppModelDeploy obj
    :param state: Current state
    :param last_transition_time: If not given, use current time.
    """
    if last_transition_time is None:
        last_transition_time = timezone.now()

    dp.status = state.status
    dp.reason = state.reason
    dp.message = state.message
    dp.last_transition_time = last_transition_time
    dp.save(update_fields=["status", "reason", "message", "last_transition_time", "updated"])


def deploy_status_to_job_status(status: DeployStatus) -> JobStatus:
    if status == DeployStatus.READY:
        return JobStatus.SUCCESSFUL
    elif status == DeployStatus.ERROR:
        return JobStatus.FAILED
    return JobStatus.PENDING
