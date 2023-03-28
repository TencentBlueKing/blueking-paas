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
"""Wait processes to match certain conditions"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

import django.dispatch
from blue_krill.async_utils.poll_task import PollingMetadata, PollingResult, PollingStatus, TaskPoller
from pydantic import BaseModel, validator

from paas_wl.workloads.processes.controllers import get_processes_status
from paasng.engine.models import Deployment
from paasng.engine.processes.events import ProcEventsProducer
from paasng.engine.processes.models import PlainProcess, condense_processes
from paasng.engine.processes.utils import ProcessesSnapshotStore
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)

processes_updated = django.dispatch.Signal(providing_args=['events', 'extra_params'])


def wait_for_all_stopped(env: ModuleEnvironment, result_handler: Type, extra_params: Optional[Dict] = None):
    """Wait for processes to be fully stopped

    :param env: ModuleEnvironment object
    :param result_handler: type to handle poll result
    :param extra_params: extra params, use it to provide data for result handler
    """
    extra_params = extra_params or {}
    params = {'env_id': env.pk, 'extra_params': extra_params}
    WaitForAllStopped.start(params, result_handler)


def wait_for_release(
    env: ModuleEnvironment, release_version: int, result_handler: Type, extra_params: Optional[Dict] = None
):
    """Wait for processes to be updated to given release version, includes all process instances

    :param env: ModuleEnvironment object
    :param release_version: release version, included in each instance
    :param result_handler: type to handle poll result
    :param extra_params: extra params, use it to provide data for result handler
    """
    extra_params = extra_params or {}
    params = {
        'env_id': env.pk,
        'broadcast_enabled': True,
        'release_version': release_version,
        'extra_params': extra_params,
    }
    WaitForReleaseAllReady.start(params, result_handler)


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
    def evaluate(self, processes: List[PlainProcess], already_waited: float, extra_params: Dict) -> bool:
        """Determine if current wait procedure should be aborted

        :param processes: current process list
        :param already_waited: how long since current procedure has been started, in seconds
        :param extra_params: extra params of current procedure
        """


class WaitProcedurePoller(TaskPoller):
    """Base class of process waiting procedure

    `params` schema:

    :param module_env_id: id of ModuleEnvironment object
    :param broadcast_enabled: whether to broadcast processes updated events
    """

    max_retries_on_error = 30
    overall_timeout_seconds = 15 * 60
    default_retry_delay_seconds = 2

    # Abort policies were extra rules which were used to break current polling procedure
    abort_policies: List[AbortPolicy] = []

    def __init__(self, params: Dict, metadata: PollingMetadata):
        super().__init__(params, metadata)
        self.env = ModuleEnvironment.objects.get(pk=self.params['env_id'])

        self.broadcast_enabled = bool(self.params.get('broadcast_enabled'))
        self.extra_params = self.params.get('extra_params', {})
        self.store = ProcessesSnapshotStore(self.env)

    def query(self) -> PollingResult:
        """Start polling query"""
        current_processes = self._get_current_processes()

        already_waited = time.time() - self.metadata.query_started_at
        logger.info(f'wait procedure started {already_waited} seconds, env: {self.env}')
        # Check all abort policies
        for policy in self.abort_policies:
            if policy.evaluate(current_processes, already_waited, self.extra_params):
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

        if self.broadcast_enabled:
            self.broadcast_events(current_processes)

        polling_result = self.get_status(current_processes)
        if polling_result.status != PollingStatus.DOING:
            # reserve original data in `extra_data` field
            polling_result.data = AbortedDetails(aborted=False, extra_data=polling_result.data).dict()
        return polling_result

    def broadcast_events(self, current_processes: List[PlainProcess]):
        """Broadcast processes/instances related events"""
        last_processes = self._get_last_processes()
        is_first_query = self.metadata.queried_count == 0
        # Try to produce events if it's not the first query, because the first query might get snapshot
        # which was stored hours ago and produce obsolete events
        if last_processes and not is_first_query:
            events = list(ProcEventsProducer(last_processes, current_processes).produce())
            if events:
                processes_updated.send(sender=self, events=events, extra_params=self.extra_params)
        self.store.save(current_processes)

    def _get_current_processes(self) -> List[PlainProcess]:
        """Get current process list"""
        wl_app = self.env.wl_app
        return condense_processes(get_processes_status(wl_app))

    def _get_last_processes(self) -> Optional[List[PlainProcess]]:
        """Get process list of last polling action"""
        try:
            return self.store.get()
        except Exception as e:
            logger.warning('Failed to get last processes, error: %s', e)
            return None

    def get_status(self, processes: List[PlainProcess]) -> PollingResult:
        raise NotImplementedError()


class DynamicReadyTimeoutPolicy(AbortPolicy):
    """Calculate overall timeout dynamically based on current replicas"""

    max_overall_timeout_seconds = 60 * 15

    def get_reason(self) -> str:
        return 'release took too long to complete'

    def evaluate(self, processes: List[PlainProcess], already_waited: float, extra_params: Dict) -> bool:
        total_desired_replicas = sum(p.replicas for p in processes)

        # Minimal timeout is 2 minutes, plus 60 seconds for every extra replica
        value = 120 + total_desired_replicas * 60
        value = min(value, self.max_overall_timeout_seconds)
        return already_waited > value


class TooManyRestartsPolicy(AbortPolicy):
    """Abort procedure when instance has been restarted for too many times"""

    maximum_count = 3

    def get_reason(self) -> str:
        return f'instance restarted more than {self.maximum_count} times'

    def evaluate(self, processes: List[PlainProcess], already_waited: float, extra_params: Dict) -> bool:
        for p in processes:
            proc_version = p.version
            for inst in p.instances:
                # Only check fresh instances which matches current process
                if inst.version != proc_version:
                    continue

                if inst.restart_count > self.maximum_count:
                    return True
        return False


class UserInterruptedPolicy(AbortPolicy):
    """Abort procedure when user requested an interruption"""

    def get_reason(self) -> str:
        return 'User interrupted release'

    @property
    def is_interrupted(self) -> bool:
        return True

    def evaluate(self, processes: List[PlainProcess], already_waited: float, extra_params: Dict) -> bool:
        deployment_id = extra_params.get('deployment_id')
        if not deployment_id:
            logger.warning('Deployment was not provided for UserInterruptedPolicy, will not proceed.')
            return False

        try:
            deployment = Deployment.objects.get(pk=deployment_id)
        except Deployment.DoesNotExist:
            logger.warning('Deployment not exists for UserInterruptedPolicy, will not proceed.')
            return False
        return bool(deployment.release_int_requested_at)


class WaitForAllStopped(WaitProcedurePoller):
    """Wait processes to fully stopped"""

    overall_timeout_seconds = 2 * 60

    def get_status(self, processes: List[PlainProcess]) -> PollingResult:
        """Check if all processes were stopped"""
        for process in processes:
            count = len(process.instances)
            if count != 0:
                logger.info(f'Process {process.type} still have {count} instances')
                return PollingResult.doing()

        logger.info(f'No instances found, all processes has been stopped for env: {self.env}')
        return PollingResult.done()


class WaitForReleaseAllReady(WaitProcedurePoller):
    """Wait for processes to updated to a specified release version"""

    abort_policies = [DynamicReadyTimeoutPolicy(), TooManyRestartsPolicy(), UserInterruptedPolicy()]
    overall_timeout_seconds = 60 * 15

    def __init__(self, params: Dict, metadata: PollingMetadata):
        super().__init__(params, metadata)
        self.release_version = int(self.params['release_version'])

    def get_status(self, processes: List[PlainProcess]) -> PollingResult:
        """Check if all where processes was updated to given release_version"""
        for process in processes:
            if not process.is_all_ready(self.release_version):
                logger.info(f'Process {process.type} was not updated to {self.release_version}, env: {self.env}')
                return PollingResult.doing()

        logger.info(f'All processes has been updated to {self.release_version}, env: {self.env}')
        return PollingResult.done()


class AbortedDetailsPolicy(BaseModel):
    """`policy` field of `AbortedDetails`"""

    reason: str
    name: str
    is_interrupted: bool = False


class AbortedDetails(BaseModel):
    """A model for storing aborted details, such as "reason" and other infos

    :param extra_data: reserved field for storing extra info
    """

    aborted: bool
    policy: Optional[AbortedDetailsPolicy]
    extra_data: Optional[Any]

    @validator('policy', always=True)
    def data_not_empty(cls, v, values, **kwargs):
        if values.get('aborted') and v is None:
            raise ValueError('"data" can not be empty when aborted is "True"!')
        return v
