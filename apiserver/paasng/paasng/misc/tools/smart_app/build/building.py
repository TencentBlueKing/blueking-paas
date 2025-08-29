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

import time
import logging
from os import PathLike

from django.conf import settings
from celery import shared_task

from blue_krill.async_utils.poll_task import PollingResult, CallbackHandler

from paasng.misc.tools.smart_app.models import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models.smart_build import SmartBuild
from paasng.misc.tools.smart_app.build.base import SmartBuildPoller
from paasng.misc.tools.smart_app.utils.output import SmartBuildStream, get_default_stream
from paasng.misc.tools.smart_app.workflow.flow import SmartBuildCoordinator, SmartBuildStateMgr, SmartBuildStep

from paasng.platform.engine.constants import JobStatus
from paasng.misc.tools.smart_app.signals import pre_phase_start, post_phase_end
from paasng.utils.i18n.celery import I18nTask

logger = logging.getLogger(__name__)


@shared_task(base=I18nTask)
def start_build(smart_build_id: str, source_url: str, package_path: PathLike, *args, **kwargs):
    """Execute smart app build task in worker

    :param smart_build_id: Id of smart build object
    """
    smart_build = SmartBuild.objects.get(pk=smart_build_id)
    smart_build_controller = SmartAppBuilder(smart_build, source_url, package_path)
    smart_build_controller.start()


@shared_task(base=I18nTask)
def start_build_error_callback(*args, **kwargs):
    context = args[0]
    exc: Exception = args[1]
    # celery.worker.request.Request own property `args` after celery==4.4.0
    smart_build_id: str = context._payload[0][0]

    state_mgr = SmartBuildStateMgr.from_smart_build_id(
        smart_build_id=smart_build_id, phase_type=SmartBuildPhaseType.BUILD
    )
    state_mgr.finish(JobStatus.FAILED, str(exc), write_to_stream=False)


class SmartAppBuilder(SmartBuildStep):
    """The main controller for building a s-mart app package"""

    def __init__(self, smart_build: SmartBuild, source_url: str, package_path: PathLike):
        self.smart_build = smart_build
        self.source_url = source_url
        self.package_path = package_path
        self.state_mgr = SmartBuildStateMgr.from_smart_build_id(
            smart_build_id=smart_build.uuid, phase_type=SmartBuildPhaseType.PREPARATION
        )
        self.stream: SmartBuildStream = get_default_stream(smart_build)
        self.coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")

    @SmartBuildStep.procedures
    def start(self):
        """Start the s-mart building process"""
        logger.info(f"Starting smart build process for build id: {self.smart_build.uuid}")

        pre_phase_start.send(self, phase=SmartBuildPhaseType.PREPARATION)
        preparation_phase = self.smart_build.phases.get(type=SmartBuildPhaseType.PREPARATION)

        with self.procedure_force_phase("校验应用描述文件", phase=preparation_phase):
            self.validate_app_description()

        with self.procedure_force_phase("校验文件目录", phase=preparation_phase):
            self.validate_file_structure()

        with self.procedure_force_phase("敏感信息扫描", phase=preparation_phase):
            self.scan_sensitive_info()

        post_phase_end.send(self, phase=SmartBuildPhaseType.PREPARATION)
        with self.procedure("启动构建阶段", phase=SmartBuildPhaseType.BUILD):
            self.async_start_building(source_url=self.source_url)

    def validate_app_description(self):
        """Validate the app description file"""

    def validate_file_structure(self):
        """Validate file and directory structure"""

    def scan_sensitive_info(self):
        """Scan for sensitive information in the package"""

    def async_start_building(self):
        """Start a new s-mart build process and check status periodically"""
        build_process_id = self.launch_build_processes(source_url=self.source_url)
        self.state_mgr.update()


class BuildProcessPoller(SmartBuildPoller):
    """Poller for querying the status of build process
    Finish when the building process in engine side was completed
    """

    max_retries_on_error = 10
    overall_timeout_seconds = settings.BUILD_PROCESS_TIMEOUT
    default_retry_delay_seconds = 2

    def query(self) -> PollingResult:
        smart_build = SmartBuild.objects.get(pk=self.params["smart_build_id"])

    def update_steps(self, smart_build: SmartBuild):
        """Update deploy steps by processing all log lines of build process."""
        # Update deploy steps by log line
        phase = smart_build.phases.get(type=SmartBuildPhaseType.BUILD)
        started_at = time.time()
        logger.info("Update s-mart build steps by log lines, smart_build: %s", self.params["smart_build_id"])

class BuildProcessResultHandler(CallbackHandler):
    """Result handler for a finished build process"""
