"""Async tasks for specs module"""
import datetime
import logging
from typing import Optional

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, PollingResult, TaskPoller
from django.utils import timezone

from paas_wl.platform.applications.struct_models import ModuleEnv, get_structured_app

from .constants import DeployStatus
from .models import AppModelDeploy
from .resource import ModelResState, MresConditionParser, get_mres_from_cluster

logger = logging.getLogger(__name__)


class AppModelDeployStatusPoller(TaskPoller):
    """A task poller to query status for fresh AppModelDeploy objects

    It takes below params:

    - deploy_id: int, ID of AppModelDeploy object
    """

    # over 30 min considered as timeout
    overall_timeout_seconds = 1800

    def query(self) -> PollingResult:
        dp = AppModelDeploy.objects.get(id=self.params['deploy_id'])
        mres = get_mres_from_cluster(dp.environment)
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

    @staticmethod
    def get_env(env_id: int) -> ModuleEnv:
        app = get_structured_app(env_id=env_id)
        return app.get_env_by_id(env_id)


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
