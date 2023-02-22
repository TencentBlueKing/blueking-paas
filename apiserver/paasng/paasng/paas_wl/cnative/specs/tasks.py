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
"""Async tasks for specs module"""
import datetime
import logging
from typing import Optional

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, PollingResult, TaskPoller
from django.utils import timezone

from paas_wl.cnative.specs.constants import DeployStatus
from paas_wl.cnative.specs.models import AppModelDeploy
from paas_wl.cnative.specs.resource import ModelResState, MresConditionParser
from paasng.paas_wl.cnative.specs.resource import get_mres_from_cluster
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class AppModelDeployStatusPoller2(TaskPoller):
    """A task poller to query status for fresh AppModelDeploy objects

    It takes below params:

    - deploy_id: int, ID of AppModelDeploy object
    """

    # over 30 min considered as timeout
    overall_timeout_seconds = 1800

    def query(self) -> PollingResult:
        dp = AppModelDeploy.objects.get(id=self.params['deploy_id'])
        mres = get_mres_from_cluster(
            ModuleEnvironment.objects.get(
                application_id=dp.application_id, module_id=dp.module_id, environment=dp.environment_name
            )
        )
        if not mres:
            return PollingResult.doing()

        state = MresConditionParser(mres).detect_state()
        if DeployStatus.is_stable(state.status):
            return PollingResult.done(data={'state': state, 'last_update': mres.status.lastUpdate})
        elif state.status == DeployStatus.PROGRESSING:
            # Also update status when it's progressing
            update_status(dp, state, last_transition_time=mres.status.lastUpdate)
        # Still pending, do another query later
        return PollingResult.doing()


class DeployStatusHandler(CallbackHandler):
    """Result handler for AppModelDeployStatusPoller"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        dp = AppModelDeploy.objects.get(id=poller.params['deploy_id'])
        if result.is_exception:
            logger.warning('Error polling AppModelDeploy status, result: %s', result)
            state = ModelResState(DeployStatus.ERROR, 'internal', 'error polling deploy status')
            update_status(dp, state)
        else:
            logger.info('Update AppModelDeploy status with data: %s', result.data)
            update_status(dp, result.data['state'], last_transition_time=result.data['last_update'])


def update_status(dp: AppModelDeploy, state: ModelResState, last_transition_time: Optional[datetime.datetime] = None):
    """Update deployment status, `last_transition_time` will always be updated

    :param db: The deploy obj
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
