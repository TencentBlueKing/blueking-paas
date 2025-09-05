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

import logging
from typing import Dict, Optional, Type

from blue_krill.async_utils.poll_task import (
    CallbackHandler,
    CallbackResult,
    PollingResult,
    PollingStatus,
    TaskPoller,
)
from django.conf import settings

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.platform.engine.constants import JobStatus

from .flow import SmartBuildCoordinator, SmartBuildStateMgr

logger = logging.getLogger(__name__)


class BuildProcessPoller(TaskPoller):
    """Poller for querying the status of build process
    Finish when the building process in engine side was completed
    """

    max_retries_on_error = 10
    overall_timeout_seconds = settings.SMART_BUILD_PROCESS_TIMEOUT
    default_retry_delay_seconds = 2

    @classmethod
    def start(cls, params: Dict, callback_handler_cls: Optional[Type] = None):
        smart_build = SmartBuildRecord.objects.get(pk=params["smart_build_id"])
        SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}").update_polling_time()
        super().start(params, callback_handler_cls)

    def query(self) -> PollingResult:
        smart_build = SmartBuildRecord.objects.get(pk=self.params["smart_build_id"])

        build_status = smart_build.status

        status = PollingStatus.DOING
        if build_status in JobStatus.get_finished_states():
            status = PollingStatus.DONE
        else:
            coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
            # 若判断任务状态超时，则认为任务失败，否则更新上报状态时间
            if coordinator.is_status_polling_timeout:
                logger.warning(
                    "Polling status of smart_build [%s] timed out, consider it failed",
                    self.params["smart_build_id"],
                )
                build_status = JobStatus.FAILED
                status = PollingStatus.DONE
            else:
                coordinator.update_polling_time()

        result = {"smart_build_id": smart_build.uuid, "build_status": build_status}
        logger.info(
            'The status of smart_build process [%s] is "%s"',
            self.params["smart_build_id"],
            build_status,
        )
        return PollingResult(status=status, data=result)


class BuildProcessResultHandler(CallbackHandler):
    """Result handler for a finished build process"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        """Callback for finished build process"""
        smart_build_id = poller.params["smart_build_id"]
        state_mgr = SmartBuildStateMgr.from_smart_build_id(
            smart_build_id=smart_build_id,
            phase_type=SmartBuildPhaseType.BUILD,
        )

        build_status = result.data["build_status"]
        logger.info("Handling result for s-mart build: %s, status: %s", smart_build_id, build_status)

        if build_status == JobStatus.SUCCESSFUL:
            state_mgr.finish(build_status)
            logger.info("S-mart build %s succeeded", smart_build_id)
        else:
            error_message = "Build process failed or timed out"
            state_mgr.finish(status=build_status, err_detail=error_message)
            logger.error("S-mart build %s failed: %s", smart_build_id, error_message)
