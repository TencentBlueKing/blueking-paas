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
"""Async components for deploy"""
import logging
from typing import Dict, Optional, Type

from blue_krill.async_utils.poll_task import PollingResult, PollingStatus, TaskPoller
from blue_krill.redis_tools.messaging import StreamChannelSubscriber

from paasng.engine.constants import BuildStatus, JobStatus
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.infras import DeploymentCoordinator, MessageParser, MessageStepMatcher
from paasng.engine.models import Deployment
from paasng.engine.models.phases import DeployPhaseTypes
from paasng.platform.core.storages.redisdb import get_default_redis

logger = logging.getLogger(__name__)


class DeployPoller(TaskPoller):
    """BasePoller for querying the status of deployment operation, will auto refresh polling time before task start"""

    @classmethod
    def start(cls, params: Dict, callback_handler_cls: Optional[Type] = None):
        deployment = Deployment.objects.get(pk=params['deployment_id'])
        DeploymentCoordinator(deployment.app_environment).update_polling_time()
        super().start(params, callback_handler_cls)


class BuildProcessPoller(DeployPoller):
    """Poller for querying the status of build process
    Finish when the building process in engine side was completed
    """

    max_retries_on_error = 10
    overall_timeout_seconds = 60 * 15
    default_retry_delay_seconds = 2

    @staticmethod
    def get_subscriber(channel_id) -> Optional[StreamChannelSubscriber]:
        subscriber = StreamChannelSubscriber(channel_id, redis_db=get_default_redis())
        channel_state = subscriber.get_channel_state()
        if channel_state == 'none':
            return None

        return subscriber

    def query(self) -> PollingResult:
        deployment = Deployment.objects.get(pk=self.params['deployment_id'])

        client = EngineDeployClient(deployment.get_engine_app())
        build_proc = client.get_build_process(self.params['build_process_id'])

        subscriber = self.get_subscriber(self.params['deployment_id'])
        phase = deployment.deployphase_set.get(type=DeployPhaseTypes.BUILD)
        pattern_maps = {
            JobStatus.PENDING: phase.get_started_pattern_map(),
            JobStatus.SUCCESSFUL: phase.get_finished_pattern_map(),
        }
        logger.info("[%s] going to get history events from redis", self.params['deployment_id'])
        if subscriber:
            for e in subscriber.get_history_events():
                event = MessageParser.parse_msg(e)
                if not event:
                    continue

                MessageStepMatcher.match_and_update_step(event, pattern_maps, phase)
        logger.info("[%s] history events from redis fetched", self.params['deployment_id'])

        build_status = build_proc.status
        build_id = str(build_proc.build_id) if build_proc.build_id else None

        status = PollingStatus.DOING
        if build_status in BuildStatus.get_finished_states():
            status = PollingStatus.DONE
        else:
            coordinator = DeploymentCoordinator(deployment.app_environment)
            # 若判断任务状态超时，则认为任务失败，否则更新上报状态时间
            if coordinator.status_polling_timeout:
                logger.warning(
                    "[deploy_id=%s, build_process_id=%s] polling build status timeout, regarding as failed by PaaS",
                    self.params["deployment_id"],
                    self.params["build_process_id"],
                )
                build_status = BuildStatus.FAILED
                status = PollingStatus.DONE
            else:
                coordinator.update_polling_time()

        result = {"build_id": build_id, "build_status": build_status}
        logger.info("[%s] got build status [%s][%s]", self.params['deployment_id'], build_id, build_status)
        return PollingResult(status=status, data=result)


class CommandPoller(DeployPoller):
    """Poller for querying the status of a user command
    Finish when the command in engine side was completed
    """

    def query(self) -> PollingResult:
        deployment = Deployment.objects.get(pk=self.params['deployment_id'])

        client = EngineDeployClient(deployment.get_engine_app())
        command_status = client.get_command_status(self.params['command_id'])

        coordinator = DeploymentCoordinator(deployment.app_environment)
        # 若判断任务状态超时，则认为任务失败，否则更新上报状态时间
        if coordinator.status_polling_timeout:
            command_status = JobStatus.FAILED
        else:
            coordinator.update_polling_time()

        if command_status in JobStatus.get_finished_states():
            poller_status = PollingStatus.DONE
        else:
            poller_status = PollingStatus.DOING

        result = {"command_status": command_status}
        return PollingResult(status=poller_status, data=result)
