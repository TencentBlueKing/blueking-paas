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


class SmartBuildProcessPoller(TaskPoller):
    """S-Mart build process status poller"""

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
            if coordinator.is_status_polling_timeout:
                logger.warning("Build [%s] poll timed out, failed.", self.params["smart_build_id"])
                build_status = JobStatus.FAILED
                status = PollingStatus.DONE
            else:
                coordinator.update_polling_time()

        logger.info("Build process [%s] status: %s", self.params["smart_build_id"], build_status)
        return PollingResult(status=status, data={"smart_build_id": smart_build.uuid, "build_status": build_status})


class SmartBuildProcessResultHandler(CallbackHandler):
    """S-Mart build process result processor"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        """Handle the callback of construction completion"""
        smart_build_id = poller.params["smart_build_id"]
        dest_put_url = poller.params["dest_put_url"]
        state_mgr = SmartBuildStateMgr.from_smart_build_id(smart_build_id, SmartBuildPhaseType.BUILD)
        build_status = result.data["build_status"]
        smart_build = state_mgr.smart_build

        if build_status == JobStatus.SUCCESSFUL:
            smart_build.artifact_url = dest_put_url
            smart_build.save()
            state_mgr.finish(build_status)
        else:
            state_mgr.finish(build_status, err_detail="Build process failed or timed out")

        SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}").release_lock(smart_build)
